import torch
import pandas as pd

from transformers import AutoTokenizer, AutoModel


threshold = 0.779
tokenizer = AutoTokenizer.from_pretrained('tokenizer/tokenizer-32k-total')
model = AutoModel.from_pretrained('1802631-steps/')
device = torch.device("cuda")
model.to(device)
model.eval()

def cos_sim(row, eps=1e-08, mode='mean'):
    a, b = row
    a, b = a['last_hidden_state'].detach().cpu().mean(dim=1).squeeze(), b['last_hidden_state'].detach().cpu().mean(dim=1).squeeze()
    
    numerator = a @ b
    a_l2, b_l2 = a @ a, b @ b
    denominator = torch.sqrt(torch.mul(a_l2, b_l2)) + torch.tensor(eps)
    return torch.div(numerator,denominator).item()
    

def get_logits(row):
    a = {k: v.to(device) for k, v in row[0].items()}
    b = {k: v.to(device) for k, v in row[1].items()}
    output_a = model(**a)
    output_b = model(**b)
    output_a = {k:v.detach().cpu() for k, v in output_a.items()}
    output_b = {k:v.detach().cpu() for k, v in output_b.items()}

    return output_a, output_b


def get_metric(preds, labels, threshold):
    preds = (preds >= threshold)

    labels = labels.values
    preds = preds.values

    tp = ((labels == 1) & (preds == 1)).sum()
    fn = ((labels == 1) & (preds == 0)).sum()
    fp = ((labels == 0) & (preds == 1)).sum()
    tn = ((labels == 0) & (preds == 0)).sum()

    recall = tp / (tp + fn)
    precision = tp / (tp + fp)
    specificity = tn / (tn + fp)
    accuracy =  (tp + tn) / (tp + tn + fp + fn)

    return recall, precision, specificity, accuracy

# Load data
eval_data = pd.read_excel('evaluate.xlsx')

# convert to tensor
model_inputs = eval_data.apply(lambda row: (tokenizer(row['moa1'], return_tensors='pt'), tokenizer(row['moa2'], return_tensors='pt')), axis=1)

# get the logits
model_outputs = model_inputs.apply(get_logits)

# get the cosine similarity
cos_sims = model_outputs.apply(cos_sim)

# Meric
recall, precision, specificity, accuracy = get_metric(cos_sims, eval_data['label'], threshold=threshold)
print(f"recall : {recall}\nprecision : {precision}\nspecificity : {specificity}\naccuracy : {accuracy}")
