"""
協調フィルタリング推薦器（購買履歴ベース「あなたへのおすすめ」）

戦略:
- Item-Item協調フィルタリング: 「この商品を買った人は他にこれも買った」
- 疎行列(scipy)で大規模データに対応
- コサイン類似度ベース
- ユーザーの購買履歴から類似商品を集約してスコアリング
"""
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize
from typing import Optional


class CollaborativeRecommender:
    """Item-Item協調フィルタリング"""
    
    def __init__(self, recent_days: int = 90, min_interactions: int = 5):
        """
        Args:
            recent_days: 直近何日分のデータを使うか
            min_interactions: 推薦対象とする商品の最小購入回数
        """
        self.recent_days = recent_days
        self.min_interactions = min_interactions
        
        # 学習結果
        self.user_item_matrix: Optional[csr_matrix] = None
        self.item_similarity: Optional[csr_matrix] = None
        self.user_to_idx: dict = {}
        self.item_to_idx: dict = {}
        self.idx_to_item: dict = {}
        self.user_history: dict = {}  # user_id -> list of article_ids
    
    def fit(self, transactions: pd.DataFrame) -> "CollaborativeRecommender":
        """user-itemインタラクション行列を構築し、item-item類似度を計算"""
        max_date = transactions['t_dat'].max()
        cutoff = max_date - pd.Timedelta(days=self.recent_days)
        df = transactions[transactions['t_dat'] >= cutoff].copy()
        
        # 購入回数が少ない商品を除外
        item_counts = df['article_id'].value_counts()
        valid_items = item_counts[item_counts >= self.min_interactions].index
        df = df[df['article_id'].isin(valid_items)]
        
        # ID -> indexマッピング
        unique_users = df['customer_id'].unique()
        unique_items = df['article_id'].unique()
        self.user_to_idx = {u: i for i, u in enumerate(unique_users)}
        self.item_to_idx = {it: i for i, it in enumerate(unique_items)}
        self.idx_to_item = {i: it for it, i in self.item_to_idx.items()}
        
        # ユーザー履歴の保存
        self.user_history = (
            df.groupby('customer_id')['article_id']
            .apply(list)
            .to_dict()
        )
        
        # 疎行列の構築（暗黙的フィードバック=購買有無を1とする）
        rows = df['customer_id'].map(self.user_to_idx).values
        cols = df['article_id'].map(self.item_to_idx).values
        data = np.ones(len(df), dtype=np.float32)
        
        n_users = len(unique_users)
        n_items = len(unique_items)
        self.user_item_matrix = csr_matrix(
            (data, (rows, cols)), shape=(n_users, n_items)
        )
        # 同じユーザーが同じ商品を複数買った場合の重複対策（max=1）
        self.user_item_matrix.data = np.minimum(self.user_item_matrix.data, 1.0)
        
        # Item-Item類似度（コサイン類似度）
        # itemベクトル: 各商品をユーザー次元のベクトルとして表現
        item_vectors = self.user_item_matrix.T.tocsr()  # (n_items, n_users)
        item_vectors_norm = normalize(item_vectors, norm='l2', axis=1)
        # 類似度行列: (n_items, n_items)
        self.item_similarity = item_vectors_norm @ item_vectors_norm.T
        
        print(f"  Users: {n_users:,} / Items: {n_items:,}")
        print(f"  User-Item matrix density: {self.user_item_matrix.nnz / (n_users * n_items):.4%}")
        return self
    
    def recommend_for_user(
        self, customer_id: str, top_k: int = 12, exclude_purchased: bool = True
    ) -> list[str]:
        """
        ユーザーの購買履歴から類似商品を集約して推薦
        """
        if customer_id not in self.user_to_idx:
            return []  # コールドスタートなら空（呼び出し側で人気商品にフォールバック）
        
        purchased_items = self.user_history.get(customer_id, [])
        purchased_idx = [
            self.item_to_idx[item] for item in purchased_items
            if item in self.item_to_idx
        ]
        if not purchased_idx:
            return []
        
        # 購買履歴の各商品の類似商品スコアを合算
        scores = np.asarray(
            self.item_similarity[purchased_idx].sum(axis=0)
        ).flatten()
        
        # 既購入を除外
        if exclude_purchased:
            scores[purchased_idx] = -np.inf
        
        # Top-K取得
        top_indices = np.argpartition(-scores, min(top_k, len(scores) - 1))[:top_k]
        # 念のためスコア順にソート
        top_indices = top_indices[np.argsort(-scores[top_indices])]
        return [self.idx_to_item[i] for i in top_indices if scores[i] > 0]
    
    def get_similar_items(self, article_id: str, top_k: int = 8) -> list[str]:
        """ある商品に類似した商品を取得（商品ページの「関連商品」用）"""
        if article_id not in self.item_to_idx:
            return []
        
        idx = self.item_to_idx[article_id]
        scores = np.asarray(self.item_similarity[idx].todense()).flatten()
        scores[idx] = -np.inf  # 自分自身を除外
        
        top_indices = np.argpartition(-scores, min(top_k, len(scores) - 1))[:top_k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]
        return [self.idx_to_item[i] for i in top_indices if scores[i] > 0]
