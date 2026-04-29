"""
コンテンツベースフィルタリング推薦器（商品属性ベース）

戦略:
- 商品の属性（カテゴリ、色、グループ、商品タイプ）で類似度を計算
- TF-IDFやOne-Hotではなく、加重カテゴリ一致で計算（軽量）
- 協調フィルタリングが効かない新商品にも対応
- 価格帯の近さも考慮
"""
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional


class ContentBasedRecommender:
    """商品属性ベースの類似商品推薦"""
    
    def __init__(self):
        # 重要度の高い属性ほど重みを大きくする
        self.feature_weights = {
            'product_type_name': 3.0,      # 商品タイプ最重要（Tシャツ同士など）
            'product_group_name': 2.0,     # 商品グループ
            'colour_group_name': 1.5,      # 色
            'graphical_appearance_name': 1.0,
            'index_group_name': 1.5,       # ターゲット層（Ladies/Mens等）
            'department_name': 1.0,
            'garment_group_name': 1.5,
        }
        self.article_to_idx: dict = {}
        self.idx_to_article: dict = {}
        self.feature_matrix: Optional[csr_matrix] = None
        self.articles_df: Optional[pd.DataFrame] = None
    
    def fit(
        self,
        articles: pd.DataFrame,
        transactions: Optional[pd.DataFrame] = None
    ) -> "ContentBasedRecommender":
        """
        商品の特徴ベクトルを構築
        
        Args:
            articles: 商品マスタ
            transactions: 価格情報取得用（任意）
        """
        df = articles.copy()
        self.article_to_idx = {a: i for i, a in enumerate(df['article_id'].values)}
        self.idx_to_article = {i: a for a, i in self.article_to_idx.items()}
        self.articles_df = df.set_index('article_id')
        
        # 各カテゴリ属性をOne-Hotエンコード + 重み付け
        feature_blocks = []
        for col, weight in self.feature_weights.items():
            if col not in df.columns:
                continue
            encoder = OneHotEncoder(sparse_output=True, handle_unknown='ignore', dtype=np.float32)
            # カテゴリ型をstrに変換してエンコード
            encoded = encoder.fit_transform(df[[col]].astype(str))
            feature_blocks.append(encoded * weight)
        
        # 価格情報（あれば）
        if transactions is not None:
            avg_price = transactions.groupby('article_id')['price'].mean()
            df['avg_price'] = df['article_id'].map(avg_price).fillna(avg_price.median())
            scaler = MinMaxScaler()
            price_scaled = scaler.fit_transform(df[['avg_price']]) * 0.5  # 価格は弱めに
            feature_blocks.append(csr_matrix(price_scaled.astype(np.float32)))
        
        self.feature_matrix = hstack(feature_blocks).tocsr()
        # L2正規化（コサイン類似度用）
        from sklearn.preprocessing import normalize
        self.feature_matrix = normalize(self.feature_matrix, norm='l2', axis=1)
        
        print(f"  Articles: {len(df):,}")
        print(f"  Feature dim: {self.feature_matrix.shape[1]}")
        return self
    
    def get_similar_items(self, article_id: str, top_k: int = 8) -> list[str]:
        """商品の類似アイテムを取得"""
        if article_id not in self.article_to_idx:
            return []
        
        idx = self.article_to_idx[article_id]
        target_vec = self.feature_matrix[idx]
        
        # 全商品との類似度（疎行列の内積）
        scores = (self.feature_matrix @ target_vec.T).toarray().flatten()
        scores[idx] = -1  # 自分自身を除外
        
        top_indices = np.argpartition(-scores, min(top_k, len(scores) - 1))[:top_k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]
        return [self.idx_to_article[i] for i in top_indices]
    
    def get_similar_items_batch(
        self, article_ids: list[str], top_k: int = 8
    ) -> dict[str, list[str]]:
        """複数商品をバッチで処理（高速）"""
        result = {}
        for aid in article_ids:
            result[aid] = self.get_similar_items(aid, top_k)
        return result
