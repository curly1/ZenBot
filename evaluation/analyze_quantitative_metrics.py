import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_curve, auc, confusion_matrix
)

def encode_labels(y):
    valid = y.isin(['TP', 'FP', 'TN', 'FN'])
    y_pred = y[valid].isin(['TP', 'FP']).astype(int)
    y_true = y[valid].isin(['TP', 'FN']).astype(int)
    return y_true, y_pred, valid

def compute_metrics(y_true, y_pred):
    if len(y_true) == 0 or len(y_pred) == 0:
        return None

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()

    fpr = fp / (fp + tn) if (fp + tn) else 0
    fnr = fn / (fn + tp) if (fn + tp) else 0

    if len(np.unique(y_true)) > 1:
        fpr_curve, tpr_curve, _ = roc_curve(y_true, y_pred)
        auc_score = auc(fpr_curve, tpr_curve)
        has_roc = True
    else:
        fpr_curve, tpr_curve, auc_score = [], [], 0.0
        has_roc = False

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "fpr": fpr,
        "fnr": fnr,
        "fpr_curve": fpr_curve,
        "tpr_curve": tpr_curve,
        "auc": auc_score,
        "has_roc": has_roc
    }

def plot_roc(fpr, tpr, title, output_dir):
    plt.figure()
    plt.plot(fpr, tpr, label=f'ROC curve (area = {auc(fpr, tpr):.2f})')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.title(f'ROC Curve - {title}')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.legend(loc="lower right")
    plt.grid(True)

    filepath = os.path.join(output_dir, f"roc_curve_{title}.png")
    plt.savefig(filepath)
    plt.close()
    print(f"📈 ROC curve saved to: {filepath}")

def analyze_intent_and_latency(df):
    metrics_list = []

    print("\n--- Intent Classification Metrics ---")

    # Normalize intent labels
    df['intent_is_correct'] = df['intent_is_correct'].str.strip().str.lower()

    # Intent metrics
    known_intents = df[df['intent_is_correct'] != 'unknown']
    total_known = len(known_intents)
    accuracy = (known_intents['intent_is_correct'] == 'yes').sum() / total_known if total_known > 0 else np.nan
    error_rate = (known_intents['intent_is_correct'] == 'no').sum() / total_known if total_known > 0 else np.nan
    unknown_ratio = (df['intent_is_correct'] == 'unknown').mean()

    print(f"Accuracy (yes): {accuracy:.3f}" if not np.isnan(accuracy) else "Accuracy: N/A")
    print(f"Error rate (no): {error_rate:.3f}" if not np.isnan(error_rate) else "Error rate: N/A")
    print(f"Unknown intent ratio: {unknown_ratio:.3f}")

    metrics_list.append({
        "metric_group": "intent",
        "accuracy": round(accuracy, 3) if not np.isnan(accuracy) else None,
        "error_rate": round(error_rate, 3) if not np.isnan(error_rate) else None,
        "unknown_ratio": round(unknown_ratio, 3)
    })

    print("\n--- Response Time Statistics (seconds) ---")
    df['response_time'] = df['response_time'].astype(float)
    stats = df['response_time'].describe(percentiles=[.5, .95, .99])

    for stat in ['count', 'mean', 'std', 'min', '50%', '95%', '99%', 'max']:
        print(f"{stat}: {stats[stat]:.6f}")

    threshold = 1.0
    slow_ratio = (df['response_time'] > threshold).mean()
    print(f"Proportion of responses > {threshold}s: {slow_ratio:.3f}")

    latency_metrics = {
        "metric_group": "latency",
        "mean": round(stats["mean"], 6),
        "std": round(stats["std"], 6),
        "min": round(stats["min"], 6),
        "50%": round(stats["50%"], 6),
        "95%": round(stats["95%"], 6),
        "99%": round(stats["99%"], 6),
        "max": round(stats["max"], 6),
        ">1s_ratio": round(slow_ratio, 3)
    }

    metrics_list.append(latency_metrics)
    return metrics_list

def analyze_csv(file_path):
    df = pd.read_csv(file_path)
    output_dir = os.path.dirname(file_path) or "."
    metrics_rows = []

    for error_type in ['policy_error', 'api_error']:
        print(f"\n--- Metrics for {error_type} ---")
        y_true, y_pred, valid_mask = encode_labels(df[error_type])
        metrics = compute_metrics(y_true, y_pred)
        if metrics is None:
            print(f"⚠️  Not enough valid data in '{error_type}' to compute metrics.")
            metrics_rows.append({
                "metric_group": error_type,
                "note": "Not enough valid data"
            })
        else:
            for k, v in metrics.items():
                if k not in ['fpr_curve', 'tpr_curve', 'has_roc']:
                    print(f"{k}: {v:.3f}")
            if metrics["has_roc"]:
                plot_roc(metrics['fpr_curve'], metrics['tpr_curve'], error_type, output_dir)
            else:
                print(f"ℹ️  ROC not computed for '{error_type}' due to single class.")

            metrics_rows.append({
                "metric_group": error_type,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1_score": metrics["f1_score"],
                "fpr": metrics["fpr"],
                "fnr": metrics["fnr"],
                "auc": metrics["auc"]
            })

    # Add intent + latency
    intent_latency_metrics = analyze_intent_and_latency(df)
    metrics_rows.extend(intent_latency_metrics)

    # Save to CSV
    metrics_df = pd.DataFrame(metrics_rows)
    output_csv_path = os.path.join(output_dir, "error_metrics_summary.csv")
    metrics_df.to_csv(output_csv_path, index=False)
    print(f"\n📄 All metrics saved to: {output_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python evaluation/analyze_quantitative_metrics.py <path_to_output_eval_quantitative_csv>")
    else:
        analyze_csv(sys.argv[1])