"""
人気商品レコメンダー（新規ユーザー向け）

戦略:
1. 直近期間の購買数で人気度を計算
2. カテゴリ別にも人気を算出（多様性確保）
3. 季節性を考慮した重み付け
"""
import pandas as pd
import numpy as np
from typing import Optional


class PopularityRecommender:
    """直近の人気商品を推薦するシンプルかつ強力な推薦器"""
    
    def __init__(self, recent_days: int = 14, time_decay: bool = True):
        """
        Args:
            recent_days: 何日分の購買履歴を使うか
            time_decay: 直近ほど重みを大きくするか
        """
        self.recent_days = recent_days
        self.time_decay = time_decay
        self.popularity_scores: Optional[pd.Series] = None
        self.popular_by_category: dict = {}
    
    def fit(self, transactions: pd.DataFrame, articles: pd.DataFrame) -> "PopularityRecommender":
        """人気度スコアを計算"""
        max_date = transactions['t_dat'].max()
        cutoff = max_date - pd.Timedelta(days=self.recent_days)
        recent = transactions[transactions['t_dat'] >= cutoff].copy()
        
        if self.time_decay:
            # 直近ほど重みを大きく(指数減衰)
            days_ago = (max_date - recent['t_dat']).dt.days
            recent['weight'] = np.exp(-days_ago / 7)  # 半減期1週間
            self.popularity_scores = (
                recent.groupby('article_id')['weight'].sum()
                .sort_values(ascending=False)
            )
        else:
            self.popularity_scores = (
                recent['article_id'].value_counts()
            )
        
        # カテゴリ別人気も計算（多様性確保用）
        merged = recent.merge(
            articles[['article_id', 'product_group_name', 'index_name']],
            on='article_id', how='left'
        )
        for cat, group in merged.groupby('index_name', observed=True):
            self.popular_by_category[cat] = (
                group['article_id'].value_counts().head(50).index.tolist()
            )
        return self
    
    def recommend(self, top_k: int = 12, diversify: bool = True) -> list[str]:
        """
        Args:
            top_k: 推薦数
            diversify: カテゴリの多様性を確保するか
        """
        if self.popularity_scores is None:
            raise RuntimeError("fit()を先に実行してください")
        
        if not diversify:
            return self.popularity_scores.head(top_k).index.tolist()
        
        # カテゴリをラウンドロビンで取り出して多様性を確保
        result = []
        seen = set()
        cat_iters = {cat: iter(items) for cat, items in self.popular_by_category.items()}
        
        while len(result) < top_k and cat_iters:
            for cat in list(cat_iters.keys()):
                try:
                    item = next(cat_iters[cat])
                    if item not in seen:
                        result.append(item)
                        seen.add(item)
                        if len(result) >= top_k:
                            break
                except StopIteration:
                    del cat_iters[cat]
        
        # 足りない場合は全体人気から補完
        if len(result) < top_k:
            for item in self.popularity_scores.index:
                if item not in seen:
                    result.append(item)
                    seen.add(item)
                    if len(result) >= top_k:
                        break
        
        return result[:top_k]
    
    def recommend_by_age_group(
        self,
        transactions: pd.DataFrame,
        customers: pd.DataFrame,
        articles: pd.DataFrame,
        age_min: int,
        age_max: int,
        top_k: int = 12
    ) -> list[str]:
        """年齢層に絞った人気商品推薦"""
        target_customers = customers[
            (customers['age'] >= age_min) & (customers['age'] <= age_max)
        ]['customer_id']
        
        max_date = transactions['t_dat'].max()
        cutoff = max_date - pd.Timedelta(days=self.recent_days)
        recent = transactions[
            (transactions['t_dat'] >= cutoff) &
            (transactions['customer_id'].isin(target_customers))
        ]
        return recent['article_id'].value_counts().head(top_k).index.tolist()
