"""
全レコメンドを事前計算してJSON/CSVに書き出す（性別セグメント対応版）

使い方:
    python src/build_recommendations.py

出力:
    output/recommendations.json   : 統合レコメンド（性別セグメント込み）
    output/articles_meta.json     : 商品メタ情報（性別タグ付き）

性別セグメント:
    - ladies: Ladieswear, Divided
    - men:    Menswear
    - kids:   Baby/Children
"""
import sys
import json
from pathlib import Path
from tqdm import tqdm
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_articles, load_customers, load_transactions
from src.recommenders import (
    PopularityRecommender,
    CollaborativeRecommender,
    ContentBasedRecommender,
)

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
IMAGES_DIR = PROJECT_ROOT / "data" / "images_128_128"
OUTPUT_DIR.mkdir(exist_ok=True)

# サンプリング比率（0.05〜1.0）
TRANSACTION_SAMPLE_FRAC = 0.05

# レコメンドを事前計算するユーザー数（各セグメントごと）
TOP_USERS_PER_SEGMENT = 3000

# 関連商品を事前計算する商品数（各セグメントごと）
TOP_ARTICLES_FOR_RELATED_PER_SEGMENT = 1500


# ========== 性別セグメントの定義 ==========
SEGMENT_MAPPING = {
    'Ladieswear': 'ladies',
    'Divided': 'ladies',           # Dividedは若年女性向け
    'Menswear': 'men',
    'Baby/Children': 'kids',
}

ALL_SEGMENTS = ['ladies', 'men', 'kids']


def get_segment(index_group_name) -> str:
    """index_group_name から性別セグメントを取得"""
    return SEGMENT_MAPPING.get(str(index_group_name), '_other')


def build_image_index(images_dir: Path) -> set:
    """images_128_128/ 配下に存在するarticle_idのセットを返す"""
    if not images_dir.exists():
        print(f"⚠️  画像フォルダが見つかりません: {images_dir}")
        return set()

    print(f"  画像インデックスを構築中... ({images_dir})")
    available = set()
    for subdir in tqdm(list(images_dir.iterdir()), desc="  Scanning"):
        if subdir.is_dir():
            for img_file in subdir.glob("*.jpg"):
                article_id = img_file.stem
                available.add(article_id)
    print(f"  ✅ 画像のある商品: {len(available):,} 件")
    return available


def compute_segment_recommendations(
    segment_name: str,
    articles_seg: pd.DataFrame,
    customers: pd.DataFrame,
    transactions_seg: pd.DataFrame,
) -> dict:
    """1セグメント分のレコメンドを計算"""
    print(f"\n--- セグメント '{segment_name}' のレコメンド計算 ---")
    print(f"  Articles: {len(articles_seg):,} / Transactions: {len(transactions_seg):,}")

    if len(transactions_seg) == 0:
        print(f"  ⚠️  トランザクションが空のためスキップ")
        return {'popular': {'overall': [], 'by_age': {}}, 'related': {}, 'users': {}}

    article_counts = transactions_seg['article_id'].value_counts()

    # 1. 人気商品
    print(f"  [1/3] 人気商品...")
    pop_rec = PopularityRecommender(recent_days=14, time_decay=True)
    pop_rec.fit(transactions_seg, articles_seg)
    popular = {
        'overall': pop_rec.recommend(top_k=60, diversify=True),
        'by_age': {
            'young': pop_rec.recommend_by_age_group(
                transactions_seg, customers, articles_seg, 16, 25, 12
            ),
            'middle': pop_rec.recommend_by_age_group(
                transactions_seg, customers, articles_seg, 26, 40, 12
            ),
            'senior': pop_rec.recommend_by_age_group(
                transactions_seg, customers, articles_seg, 41, 80, 12
            ),
        }
    }
    print(f"    → overall: {len(popular['overall'])} 件")

    # 2. 関連商品（コンテンツベース）
    print(f"  [2/3] 関連商品（コンテンツベース）...")
    cb_rec = ContentBasedRecommender()
    cb_rec.fit(articles_seg, transactions_seg)

    top_articles_for_related = (
        article_counts.head(TOP_ARTICLES_FOR_RELATED_PER_SEGMENT).index.tolist()
    )
    related = {}
    for aid in tqdm(top_articles_for_related, desc=f"    {segment_name}/related"):
        related[aid] = cb_rec.get_similar_items(aid, top_k=8)
    print(f"    → {len(related)} 商品分")

    # 3. ユーザー別レコメンド（協調FL）
    print(f"  [3/3] ユーザー別レコメンド（協調フィルタリング）...")
    cf_rec = CollaborativeRecommender(recent_days=90, min_interactions=3)
    cf_rec.fit(transactions_seg)

    top_users = (
        transactions_seg['customer_id'].value_counts()
        .head(TOP_USERS_PER_SEGMENT).index.tolist()
    )
    user_recs = {}
    for uid in tqdm(top_users, desc=f"    {segment_name}/users"):
        recs = cf_rec.recommend_for_user(uid, top_k=12)
        if recs:
            user_recs[uid] = {
                'short_id': uid[:8],
                'recommendations': recs,
            }
    print(f"    → {len(user_recs)} ユーザー分")

    return {'popular': popular, 'related': related, 'users': user_recs}


def main():
    print("=" * 60)
    print("H&M レコメンド事前計算（性別セグメント対応・画像有り商品のみ）")
    print("=" * 60)

    # データ読み込み
    print("\n[1/5] データ読み込み...")
    articles = load_articles()
    print(f"  Articles: {len(articles):,}")
    customers = load_customers()
    print(f"  Customers: {len(customers):,}")
    transactions = load_transactions(sample_frac=TRANSACTION_SAMPLE_FRAC)
    print(f"  Transactions (sampled {TRANSACTION_SAMPLE_FRAC*100:.0f}%): {len(transactions):,}")

    # 画像インデックスの構築
    print("\n[2/5] 画像インデックスの構築...")
    available_images = build_image_index(IMAGES_DIR)
    if not available_images:
        print("⚠️  画像が一つも見つかりません。data/images_128_128/ を確認してください")
        return

    # 画像のある商品のみにフィルタ
    print("\n  📌 画像のある商品のみを学習対象にします")
    articles = articles[articles['article_id'].isin(available_images)].reset_index(drop=True)
    transactions = transactions[transactions['article_id'].isin(available_images)].reset_index(drop=True)
    print(f"  画像有り商品 → Articles: {len(articles):,} / Transactions: {len(transactions):,}")

    # 商品に性別セグメントを付与
    articles['segment'] = articles['index_group_name'].apply(get_segment)
    seg_dist = articles['segment'].value_counts()
    print(f"\n  性別セグメント分布:")
    for seg, count in seg_dist.items():
        print(f"    {seg}: {count:,} 件")

    # 各商品のセグメントを取引にも伝播
    article_to_segment = articles.set_index('article_id')['segment'].to_dict()
    transactions['segment'] = transactions['article_id'].map(article_to_segment)

    # 商品メタ情報の出力
    print("\n[3/5] 商品メタ情報の出力...")
    article_counts = transactions['article_id'].value_counts()
    avg_prices = transactions.groupby('article_id')['price'].mean()

    articles_meta = {}
    relevant_articles = articles[articles['article_id'].isin(article_counts.index)]
    for _, row in tqdm(relevant_articles.iterrows(), total=len(relevant_articles)):
        aid = row['article_id']
        articles_meta[aid] = {
            'id': aid,
            'name': row.get('prod_name', ''),
            'product_type': str(row.get('product_type_name', '')),
            'product_group': str(row.get('product_group_name', '')),
            'colour': str(row.get('colour_group_name', '')),
            'index_name': str(row.get('index_name', '')),
            'index_group': str(row.get('index_group_name', '')),
            'department': str(row.get('department_name', '')),
            'description': str(row.get('detail_desc', ''))[:200],
            'price': float(avg_prices.get(aid, 0.0)),
            'segment': str(row.get('segment', '_other')),  # ladies/men/kids/_other
            'has_image': True,
            'image_url': f"/images/{aid[:3]}/{aid}.jpg",
        }

    with open(OUTPUT_DIR / "articles_meta.json", "w", encoding="utf-8") as f:
        json.dump(articles_meta, f, ensure_ascii=False)
    print(f"  → {len(articles_meta):,} 件保存")

    # 各セグメントごとにレコメンド計算
    print("\n[4/5] セグメント別レコメンド計算...")
    segment_data = {}
    for seg in ALL_SEGMENTS:
        articles_seg = articles[articles['segment'] == seg].reset_index(drop=True)
        transactions_seg = transactions[transactions['segment'] == seg].reset_index(drop=True)
        segment_data[seg] = compute_segment_recommendations(
            seg, articles_seg, customers, transactions_seg
        )

    # 全体（HOMEタブ用）でも計算
    print("\n--- 全体（all）のレコメンド計算 ---")
    segment_data['all'] = compute_segment_recommendations(
        'all', articles, customers, transactions
    )

    # 統合JSON作成
    print("\n[5/5] 統合レコメンドJSONの作成...")

    # 全セグメントのユーザーIDをマージしてサンプル抽出
    all_sample_users = []
    for seg in ALL_SEGMENTS + ['all']:
        all_sample_users.extend(list(segment_data[seg]['users'].keys())[:5])
    all_sample_users = list(dict.fromkeys(all_sample_users))[:20]  # 重複排除

    combined = {
        'segments': {
            seg: {
                'popular_articles': segment_data[seg]['popular'],
                'related_articles': segment_data[seg]['related'],
                'user_recommendations': segment_data[seg]['users'],
            }
            for seg in ALL_SEGMENTS + ['all']
        },
        'meta': {
            'available_segments': ALL_SEGMENTS + ['all'],
            'n_articles_with_meta': len(articles_meta),
            'segment_article_counts': {
                seg: int((articles['segment'] == seg).sum())
                for seg in ALL_SEGMENTS + ['_other']
            },
            'sample_user_ids': all_sample_users,
        }
    }
    with open(OUTPUT_DIR / "recommendations.json", "w") as f:
        json.dump(combined, f)
    print(f"  → output/recommendations.json 作成完了")

    print("\n" + "=" * 60)
    print("✅ 全レコメンドの事前計算が完了しました")
    print("各セグメントの統計:")
    for seg in ALL_SEGMENTS + ['all']:
        d = segment_data[seg]
        n_pop = len(d['popular']['overall'])
        n_rel = len(d['related'])
        n_usr = len(d['users'])
        print(f"  {seg:8s}: popular={n_pop}, related={n_rel}, users={n_usr}")
    print("\n次のステップ: python api/server.py でAPIを起動")
    print("=" * 60)


if __name__ == "__main__":
    main()