"""
H&Mデータセット読み込みモジュール
メモリ効率を考慮し、必要なカラムのみ・適切なdtypeで読み込む
"""
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_articles() -> pd.DataFrame:
    """商品マスタの読み込み"""
    dtypes = {
        'article_id': 'str',
        'product_code': 'int32',
        'product_type_no': 'int16',
        'product_type_name': 'category',
        'product_group_name': 'category',
        'graphical_appearance_no': 'int32',
        'graphical_appearance_name': 'category',
        'colour_group_code': 'int8',
        'colour_group_name': 'category',
        'department_no': 'int16',
        'department_name': 'category',
        'index_code': 'category',
        'index_name': 'category',
        'index_group_no': 'int8',
        'index_group_name': 'category',
        'section_no': 'int8',
        'section_name': 'category',
        'garment_group_no': 'int16',
        'garment_group_name': 'category',
    }
    df = pd.read_csv(
        DATA_DIR / "articles.csv",
        dtype=dtypes,
        usecols=list(dtypes.keys()) + ['prod_name', 'detail_desc']
    )
    # article_idは前ゼロを保持（10桁）
    df['article_id'] = df['article_id'].str.zfill(10)
    return df


def load_customers() -> pd.DataFrame:
    """顧客マスタの読み込み"""
    df = pd.read_csv(
        DATA_DIR / "customers.csv",
        dtype={
            'customer_id': 'str',
            'FN': 'float32',
            'Active': 'float32',
            'club_member_status': 'category',
            'fashion_news_frequency': 'category',
            'age': 'float32',
            'postal_code': 'category',
        }
    )
    return df


def load_transactions(sample_frac: float | None = None) -> pd.DataFrame:
    """
    購買履歴の読み込み（巨大なため必要に応じてサンプリング）
    
    Args:
        sample_frac: サンプリング比率 (0.0-1.0)。Noneなら全件
    """
    dtypes = {
        'customer_id': 'str',
        'article_id': 'str',
        'price': 'float32',
        'sales_channel_id': 'int8',
    }
    df = pd.read_csv(
        DATA_DIR / "transactions_train.csv",
        dtype=dtypes,
        parse_dates=['t_dat']
    )
    df['article_id'] = df['article_id'].str.zfill(10)
    
    if sample_frac is not None:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
    
    return df


def load_recent_transactions(days: int = 30) -> pd.DataFrame:
    """直近N日のトランザクションのみ読み込み（メモリ節約）"""
    df = load_transactions()
    max_date = df['t_dat'].max()
    cutoff = max_date - pd.Timedelta(days=days)
    return df[df['t_dat'] >= cutoff].reset_index(drop=True)


if __name__ == "__main__":
    print("=== データロードテスト ===")
    articles = load_articles()
    print(f"Articles: {len(articles):,} 件")
    print(articles.head(3))
    print()
    
    customers = load_customers()
    print(f"Customers: {len(customers):,} 件")
    print(customers.head(3))
    print()
    
    # 全件は重いのでサンプリング
    transactions = load_transactions(sample_frac=0.01)
    print(f"Transactions (1% sample): {len(transactions):,} 件")
    print(transactions.head(3))
