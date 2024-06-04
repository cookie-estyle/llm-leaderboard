import json
from pathlib import Path
from collections import defaultdict

from jinja2 import Template

from config_singleton import WandbConfigSingleton

def get_system_message(system_message_intro: str, instruction: str):
    system_message = ""
    system_message += system_message_intro
    system_message += "\n"
    system_message += instruction
    return system_message


def get_few_shot_messages(target_dataset_path: str, num_few_shots: int):
    dataset_json_name = target_dataset_path.name
    target_few_shot_path = (
        target_dataset_path.resolve().parent.parent / "train" / dataset_json_name
    )
    assert (
        target_few_shot_path.exists()
    ), f"Wrong path {target_few_shot_path.resolve()}, can not extract few-shot samples"
    samples = json.loads(target_few_shot_path.read_text(encoding="utf-8"))["samples"]

    few_shot_messages = []
    for i in range(num_few_shots):
        few_shot_messages.append({"role": "user", "content": samples[i]["input"]})
        few_shot_messages.append({"role": "assistant", "content": samples[i]["output"]})
    return few_shot_messages


# bbqデータセットはカテゴリごとにfew-shotを構築するため、専用のカテゴリごとのfew-shotを取得する関数を追加
def get_few_shot_samples_by_bbq_category(target_dataset_path: Path, num_few_shots: int, sample_class=None) -> dict[str, list]:
    if num_few_shots == 0:
        return defaultdict(list)
    
    if sample_class is None:
        from evaluator.bbq import BBQSample
        sample_class = BBQSample
    
    dataset_json_name = target_dataset_path.name
    target_few_shot_path = target_dataset_path.resolve().parent.parent / "train" / dataset_json_name

    assert target_few_shot_path.exists(), f"Wrong path {target_few_shot_path.resolve()}, can not extract few-shot samples"

    samples_data = json.loads(target_few_shot_path.read_text(encoding="utf-8"))["samples"]

    category_samples = defaultdict(list)
    for data in samples_data:
        sample = sample_class(**data)
        category_samples[sample.category].append(sample)
    
    few_shot_samples = defaultdict(list)
    for category, samples in category_samples.items():
        selected_samples = samples[:num_few_shots]
        few_shot_samples[category].extend(selected_samples)
    
    return few_shot_samples


def apply_chat_template(messages: list[dict[str, str]]) -> str:
    instance = WandbConfigSingleton.get_instance()
    cfg = instance.config

    if cfg.api == "vllm":
        tokenizer_config = cfg.tokenizer_config
        chat_template = Template(cfg.tokenizer_config.chat_template)
        conversation_prompt = chat_template.render(
            messages=messages, add_generation_prompt=True, **tokenizer_config
        )
    else:
        conversation_prompt = json.dumps(
            messages,
            ensure_ascii=False,
            indent=2,
        )
    return conversation_prompt
