import json
import time
from pathlib import Path

import wandb
from langchain.prompts import BasePromptTemplate
from tqdm import tqdm
import pandas as pd
from toolz import pipe

from config_singleton import WandbConfigSingleton
from utils import (
    get_evaluation_prompt,
    get_few_shot_samples,
    Sample,
    normalize,
    metrics_func_dict,
    text_formatter,
)

"""
## datasetの追加方法
以下のファイルを作成・編集してください。

- 作成
    - {データセット名}_evaluation.py
        - 評価コードの作成
- 編集
    - run_eval.py
        - データセット評価関数のimport, 実行
    - config_template.py
        - データセットの設定
    - utils.py
        - 必要に応じて編集

> 実装はSaaSだけでなく、dedicated cloudでも動くように、OpenAIだけでなく、Azure OpenAIでも動くように心がけてください。
"""


def jmmlu_evaluate():
    # Retrieve the instance from WandbConfigSingleton and load the W&B run and configuration
    instance = WandbConfigSingleton.get_instance()
    run = instance.run
    cfg = instance.config
    llm = instance.llm

    # download dataset
    dataset_name = "jmmlu"
    artifact = run.use_artifact(cfg[dataset_name].artifacts_path, type="dataset")
    artifact_dir = artifact.download()
    dataset_dir = Path(artifact_dir) / cfg[dataset_name].dataset_dir
    tasks = sorted({p.stem for p in dataset_dir.glob("**/jmmlu_*.json")})

    evaluation_results = []
    for task in tasks:
        # execute evaluation
        language = cfg[dataset_name].language
        for subset in ("test", "dev"):
            eval_matainfo = {
                "run_name": run.name,
                "model_name": cfg.model.pretrained_model_name_or_path,
                "dataset": "JMMLU",
                "task": task[len("jmmlu_"):],
                "num_few_shots": cfg.num_few_shots,
                "subset": subset,
            }

            # read task data
            task_data_path = (
                dataset_dir
                / subset
                / f"{task}.json"
            )
            if not task_data_path.exists():
                print(f"skip {task} because it is not found in {artifact_dir}")
                continue
            with task_data_path.open(encoding="utf-8") as f:
                task_data = json.load(f)

            # define custom prompt template
            custom_prompt_template = cfg.get(f"custom_prompt_template_{language}", None)
            custom_fewshots_template = cfg.get(f"custom_fewshots_template_{language}", None)

            # get fewshots samples
            few_shots: list[Sample] = get_few_shot_samples(
                target_dataset_path=task_data_path,
                num_few_shots=cfg.num_few_shots,
            )

            # get prompt
            base_prompt: BasePromptTemplate = get_evaluation_prompt(
                instruction=task_data["instruction"],
                few_shots=few_shots,
                language=language,
                custom_prompt_template=custom_prompt_template,
                custom_fewshots_template=custom_fewshots_template,
            )

            # number of evaluation samples
            if cfg.testmode:
                test_max_num_samples = 1
                val_max_num_samples = 1
            else:
                test_max_num_samples = 5
                val_max_num_samples = 1

            if subset == "test":
                num_samples = test_max_num_samples
            elif subset == "dev":
                num_samples = val_max_num_samples
            samples = task_data["samples"][:num_samples]

            # llm pipline
            llm.max_tokens = task_data["output_length"]
            chain = base_prompt | llm

            for idx, sample in tqdm(enumerate(samples)):
                # generate output
                input_data = {"input": sample["input"]}
                start_time = time.time()
                output = chain.invoke(input_data)
                end_time = time.time()
                latency = end_time - start_time
                try:
                    prompt = base_prompt.format(**input_data)
                except:
                    import pdb; pdb.set_trace()

                # score
                y_pred: str = pipe(
                    output,
                    lambda x: text_formatter(x, task),
                    lambda x: x.split("\n\n")[0],
                    normalize,
                )
                y_true: str = pipe(sample["output"], normalize)
                metrics: list[str] = task_data["metrics"][0]
                metrics_func: callable = metrics_func_dict[metrics]
                score = metrics_func(y_pred, y_true)

                # collect data
                evaluation_results.append(
                    {
                        **eval_matainfo,
                        "index": idx,
                        "input": sample["input"],
                        "output": y_pred,
                        "expected_output": y_true,
                        "prompt": prompt,
                        "metrics": metrics,
                        "score": score,
                        "latency": latency,
                    }
                )

    # log table
    output_df = pd.DataFrame(evaluation_results)
    dev_table = output_df.query("subset == 'dev'")
    test_table = output_df.query("subset == 'test'")
    leaderboard_table = pd.pivot_table(
        data=test_table, values="score", index="model_name", columns="dataset", aggfunc="mean"
    ).reset_index()
    wandb.log(
        {
            f"{dataset_name}_output_table_dev": dev_table,
            f"{dataset_name}_output_table": test_table,
            f"{dataset_name}_leaderboard_table": leaderboard_table,
        }
    )
