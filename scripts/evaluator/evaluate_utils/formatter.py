import unicodedata


def normalize(input_str: str) -> str:
    return unicodedata.normalize("NFKC", input_str)

def text_formatter(input_str: str, dataset: str) -> str:
    if dataset in ["jamp", "janli", "jnli", "jsem", "jsick"]:
        output_str = input_str.strip().lower()
    elif dataset in [
        "jcommonsenseqa",
        "commonsensemoralja",
        "mawps",
        "wiki_reading",
        "wiki_ner",
        "wiki_dependency",
        "wiki_pas",
        "wiki_coreference",
    ]:
        output_str = input_str.strip()
    elif dataset in ["jemhopqa", "jsquad", "niilc"]:
        output_str = input_str.strip().lower()
        replacements = ["回答:", "回答: ", "答え:", "答え: "]
        for r in replacements:
            output_str = output_str.replace(r, "")
    elif dataset.startswith("jmmlu_IncorrectChoice"):
        output_str = input_str.strip().upper()
        replacements = ["回答:", "答え:", " "]
        for r in replacements:
            output_str = output_str.replace(r, "")
    elif dataset.startswith("jmmlu_"):
        output_str = input_str.strip().upper()
        replacements = ["回答:", "回答: ", "答え:", "答え: "]
        for r in replacements:
            output_str = output_str.replace(r, "")
    elif dataset.startswith("mmlu_en_"):
        output_str = input_str.strip().upper()
        replacements = ["ANSWER:", "ANSWER: ", "RESPONSE:", "RESPONSE: "]
        for r in replacements:
            output_str = output_str.replace(r, "")
    elif dataset in ["mawps", "chabsa"]:
        output_str = input_str.strip()
    # elif dataset in ["your_dataset_name_here"]:
    #     output_str = input_str
    else:
        output_str = input_str
    return output_str


def symbol_to_ABCD(input_str):
    mapping = {"$": "A", "&": "B", "#": "C", "@": "D"}
    return mapping.get(input_str, "")


def incorrect_to_ABCD(input_str):
    mapping = {
        "B,C,D": "A",
        "A,C,D": "B",
        "A,B,D": "C",
        "A,B,C": "D",
    }
    return mapping.get(input_str, "")