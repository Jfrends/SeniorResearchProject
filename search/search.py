import math

def map_score(returned, relevant):
    score = 0
    num_correct = 0
    for i, doc in enumerate(returned):
        if doc in relevant:
            num_correct += 1
            score += num_correct / (i+1)
    if len(relevant) > 0:
        return score / len(relevant)
    return 0

def get_doc_text(doc_name : str):
    with open(doc_name, "r") as doc:
        lines = doc.readlines()
    return " ".join(lines)

def get_judgement_df(file):
    df = {}

    with open(file, "r") as f:
        lines = f.readlines()

    for line in lines:
        vals = line.split(" ")
        vals = [int(val.strip()) for val in vals if val.strip() != ""]
        if df.get(vals[0]) is None:
            df[vals[0]] = []
        if vals[2] in {1, 2, 3}:
            df[vals[0]].append(vals[1])
    
    return df




