"""
H&MデータのEDAヘルパー関数
NotebookやスクリプトからimportしてEDAを行う
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.family'] = ['DejaVu Sans']  # 環境に応じて 'Meiryo' などに変更可


def basic_stats(df: pd.DataFrame, name: str = "DataFrame") -> None:
    """基本統計量を出力"""
    print(f"=== {name} ===")
    print(f"Shape: {df.shape}")
    print(f"Memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    print(f"Missing values:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
    print()


def top_articles(transactions: pd.DataFrame, n: int = 20) -> pd.Series:
    """売上数量Top N商品"""
    return transactions['article_id'].value_counts().head(n)


def sales_trend(transactions: pd.DataFrame) -> pd.DataFrame:
    """日次売上トレンド"""
    daily = transactions.groupby('t_dat').agg(
        n_transactions=('customer_id', 'count'),
        n_unique_customers=('customer_id', 'nunique'),
        total_revenue=('price', 'sum')
    ).reset_index()
    return daily


def plot_sales_trend(daily_sales: pd.DataFrame, figsize=(14, 4)) -> None:
    """売上トレンドの可視化"""
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    axes[0].plot(daily_sales['t_dat'], daily_sales['n_transactions'], linewidth=0.8)
    axes[0].set_title('Daily Transaction Count')
    axes[0].set_xlabel('Date')
    axes[0].set_ylabel('Transactions')
    axes[0].tick_params(axis='x', rotation=45)
    
    axes[1].plot(daily_sales['t_dat'], daily_sales['total_revenue'], linewidth=0.8, color='orange')
    axes[1].set_title('Daily Revenue')
    axes[1].set_xlabel('Date')
    axes[1].set_ylabel('Revenue')
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()


def customer_segments(customers: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    """顧客セグメント分析: 購買回数・金額・最終購買日（RFM風）"""
    rfm = transactions.groupby('customer_id').agg(
        recency=('t_dat', lambda x: (transactions['t_dat'].max() - x.max()).days),
        frequency=('article_id', 'count'),
        monetary=('price', 'sum')
    ).reset_index()
    
    # 年齢情報をマージ
    rfm = rfm.merge(customers[['customer_id', 'age']], on='customer_id', how='left')
    return rfm


def category_distribution(articles: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    """カテゴリ別売上分布"""
    merged = transactions.merge(
        articles[['article_id', 'product_group_name', 'index_name']],
        on='article_id',
        how='left'
    )
    return merged.groupby('product_group_name', observed=True).size().sort_values(ascending=False)


def seasonal_analysis(transactions: pd.DataFrame, articles: pd.DataFrame) -> pd.DataFrame:
    """月別×カテゴリの売上パターン（季節性把握）"""
    merged = transactions.merge(
        articles[['article_id', 'product_group_name']],
        on='article_id', how='left'
    )
    merged['month'] = merged['t_dat'].dt.month
    pivot = merged.pivot_table(
        index='month',
        columns='product_group_name',
        values='article_id',
        aggfunc='count',
        fill_value=0,
        observed=True
    )
    return pivot


def price_distribution_by_category(articles: pd.DataFrame, transactions: pd.DataFrame, top_n_categories=10):
    """カテゴリ別の価格分布"""
    merged = transactions.merge(
        articles[['article_id', 'product_group_name']],
        on='article_id', how='left'
    )
    top_cats = merged['product_group_name'].value_counts().head(top_n_categories).index.tolist()
    subset = merged[merged['product_group_name'].isin(top_cats)]
    
    plt.figure(figsize=(12, 5))
    sns.boxplot(data=subset, x='product_group_name', y='price', showfliers=False)
    plt.xticks(rotation=45, ha='right')
    plt.title('Price Distribution by Category (Top 10)')
    plt.tight_layout()
    plt.show()
