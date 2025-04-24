import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

def load_and_preprocess(filepath):
    df = pd.read_csv(filepath)
    for col in ['naturalness', 'coherence', 'helpfulness']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['binary_pass'] = df['binary_pass'].astype(int)
    return df

def descriptive_stats(df, output_dir):
    print("\n--- Descriptive Statistics ---")
    stats = df[['naturalness', 'coherence', 'helpfulness']].describe(percentiles=[.25, .5, .75])
    print(stats)

    stats.to_csv(os.path.join(output_dir, "descriptive_stats.csv"))
    print(f"📄 Descriptive stats saved to: {output_dir}/descriptive_stats.csv")

def correlation_analysis(df, output_dir):
    print("\n--- Correlation Analysis ---")
    corr_matrix = df[['naturalness', 'coherence', 'helpfulness', 'binary_pass']].corr(method='pearson')
    print(corr_matrix)

    # Save to CSV
    corr_matrix.to_csv(os.path.join(output_dir, "correlation_matrix.csv"))
    print(f"📄 Correlation matrix saved to: {output_dir}/correlation_matrix.csv")

    # Heatmap
    plt.figure(figsize=(6, 5))
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", fmt=".2f", square=True)
    plt.title("Score Correlation Heatmap")
    heatmap_path = os.path.join(output_dir, "correlation_heatmap.png")
    plt.savefig(heatmap_path)
    plt.close()
    print(f"📊 Correlation heatmap saved to: {heatmap_path}")

def generate_plots(df, output_dir):
    for col in ['naturalness', 'coherence', 'helpfulness']:
        # Box plot
        plt.figure()
        sns.boxplot(y=df[col])
        plt.title(f"Box Plot of {col}")
        box_path = os.path.join(output_dir, f"boxplot_{col}.png")
        plt.savefig(box_path)
        plt.close()
        print(f"📦 Box plot saved to: {box_path}")

        # Histogram
        plt.figure()
        sns.histplot(df[col], bins=5, kde=True)
        plt.title(f"Histogram of {col}")
        hist_path = os.path.join(output_dir, f"histogram_{col}.png")
        plt.savefig(hist_path)
        plt.close()
        print(f"📈 Histogram saved to: {hist_path}")

def main(filepath):
    df = load_and_preprocess(filepath)
    output_dir = os.path.dirname(filepath) or "."
    descriptive_stats(df, output_dir)
    correlation_analysis(df, output_dir)
    generate_plots(df, output_dir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python evaluation/analyze_qualitative_metrics.py <path_to_output_eval_qualitative_csv>")
    else:
        main(sys.argv[1])