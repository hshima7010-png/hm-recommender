"""
レコメンドAPIサーバー (Flask) - 性別セグメント対応版

エンドポイント:
    GET  /                                       : フロントのindex.html
    GET  /<filename>                             : フロント静的ファイル
    GET  /images/<subdir>/<filename>             : H&M商品画像

    GET  /api/article/<article_id>               : 商品詳細
    GET  /api/popular?segment=<seg>&age=<seg>   : 人気商品（性別×年齢）
    GET  /api/related/<article_id>               : 関連商品
    GET  /api/recommend/<customer_id>?segment=<seg> : ユーザー向け推薦
    GET  /api/sample-users                       : デモ用ユーザーID
    GET  /api/search?q=<query>&segment=<seg>    : 商品検索
    GET  /api/segment-info                       : セグメント情報

セグメントパラメータ:
    'all' (default), 'ladies', 'men', 'kids'
"""
import json
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
IMAGES_DIR = PROJECT_ROOT / "data" / "images_128_128"

VALID_SEGMENTS = ['all', 'ladies', 'men', 'kids']

# 起動時にデータロード
print("レコメンドデータ読み込み中...")
with open(OUTPUT_DIR / "articles_meta.json", encoding="utf-8") as f:
    ARTICLES_META = json.load(f)
with open(OUTPUT_DIR / "recommendations.json", encoding="utf-8") as f:
    RECOMMENDATIONS = json.load(f)
print(f"✅ {len(ARTICLES_META):,} 商品ロード完了")

# 利用可能セグメントを確認
available_segments = list(RECOMMENDATIONS.get('segments', {}).keys())
print(f"  利用可能セグメント: {available_segments}")

if IMAGES_DIR.exists():
    print(f"✅ 画像フォルダ検出: {IMAGES_DIR}")
else:
    print(f"⚠️  画像フォルダが見つかりません: {IMAGES_DIR}")


def hydrate_articles(article_ids: list) -> list:
    """商品IDのリストをメタ情報付きdictリストに変換（画像のある商品のみ）"""
    return [
        ARTICLES_META[aid] for aid in article_ids
        if aid in ARTICLES_META and ARTICLES_META[aid].get('has_image')
    ]


def get_segment_param() -> str:
    """リクエストからsegmentパラメータを取得（デフォルト all）"""
    seg = request.args.get('segment', 'all')
    return seg if seg in VALID_SEGMENTS else 'all'


def get_segment_data(segment: str) -> dict:
    """指定セグメントのレコメンドデータを取得"""
    return RECOMMENDATIONS.get('segments', {}).get(segment, {})


# ======== 画像配信 ========
@app.route("/images/<subdir>/<filename>")
def serve_image(subdir: str, filename: str):
    """H&M商品画像配信"""
    if ".." in subdir or ".." in filename or "/" in subdir or "/" in filename:
        abort(404)
    image_path = IMAGES_DIR / subdir / filename
    if not image_path.exists():
        abort(404)
    return send_from_directory(IMAGES_DIR / subdir, filename, max_age=3600)


# ======== 静的ファイル配信 ========
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename: str):
    return send_from_directory(FRONTEND_DIR, filename)


# ======== API ========
@app.route("/api/segment-info")
def segment_info():
    """利用可能セグメントとその統計"""
    return jsonify({
        "segments": VALID_SEGMENTS,
        "meta": RECOMMENDATIONS.get('meta', {}),
    })


@app.route("/api/article/<article_id>")
def get_article(article_id: str):
    """商品詳細"""
    if article_id not in ARTICLES_META:
        return jsonify({"error": "Article not found"}), 404
    return jsonify(ARTICLES_META[article_id])


@app.route("/api/popular")
def popular():
    """人気商品（性別 × 年齢層別）"""
    segment = get_segment_param()
    age = request.args.get("age", "overall")  # overall|young|middle|senior

    seg_data = get_segment_data(segment)
    pop_data = seg_data.get("popular_articles", {})

    if age == "overall":
        ids = pop_data.get("overall", [])
    elif age in pop_data.get("by_age", {}):
        ids = pop_data["by_age"][age]
    else:
        return jsonify({"error": "Invalid age"}), 400

    return jsonify({
        "segment": segment,
        "age": age,
        "items": hydrate_articles(ids),
    })


@app.route("/api/related/<article_id>")
def related(article_id: str):
    """関連商品（商品の所属セグメントから取得）"""
    # 商品自体のセグメントを使う
    article = ARTICLES_META.get(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    
    seg = article.get('segment', 'all')
    if seg == '_other':
        seg = 'all'
    
    seg_data = get_segment_data(seg)
    related_map = seg_data.get("related_articles", {})
    
    if article_id in related_map:
        return jsonify({
            "article_id": article_id,
            "segment": seg,
            "items": hydrate_articles(related_map[article_id])
        })
    
    # フォールバック: allセグメントの関連商品
    if seg != 'all':
        related_map_all = get_segment_data('all').get("related_articles", {})
        if article_id in related_map_all:
            return jsonify({
                "article_id": article_id,
                "segment": "all",
                "items": hydrate_articles(related_map_all[article_id]),
                "fallback": True,
            })
    
    # さらにフォールバック: 同カテゴリの画像つき商品
    target_cat = article["product_type"]
    target_seg = article.get('segment', '_other')
    same_cat = [
        a for aid, a in ARTICLES_META.items()
        if a["product_type"] == target_cat
        and aid != article_id
        and a.get("has_image")
        and (target_seg == '_other' or a.get('segment') == target_seg)
    ][:8]
    return jsonify({
        "article_id": article_id,
        "items": same_cat,
        "fallback": True,
        "fallback_type": "same_category"
    })


@app.route("/api/recommend/<customer_id>")
def recommend_for_user(customer_id: str):
    """ユーザー向けレコメンド（セグメント指定可）"""
    segment = get_segment_param()
    seg_data = get_segment_data(segment)
    user_recs = seg_data.get("user_recommendations", {})
    
    if customer_id in user_recs:
        ids = user_recs[customer_id]["recommendations"]
        return jsonify({
            "customer_id": customer_id,
            "segment": segment,
            "items": hydrate_articles(ids),
            "source": "collaborative_filtering",
        })
    
    # コールドスタート: そのセグメントの人気商品にフォールバック
    fallback_ids = seg_data.get("popular_articles", {}).get("overall", [])
    return jsonify({
        "customer_id": customer_id,
        "segment": segment,
        "items": hydrate_articles(fallback_ids),
        "source": "popularity_fallback",
        "message": "新規ユーザーのため人気商品を表示しています",
    })


@app.route("/api/sample-users")
def sample_users():
    """デモ用ユーザーID一覧（全セグメント横断）"""
    sample_ids = RECOMMENDATIONS.get("meta", {}).get("sample_user_ids", [])
    
    # 各ユーザーがどのセグメントで推薦データを持っているかも返す
    result_users = []
    all_segments = RECOMMENDATIONS.get('segments', {})
    
    for uid in sample_ids:
        segments_with_data = []
        n_recs = 0
        for seg_name, seg_data in all_segments.items():
            if uid in seg_data.get('user_recommendations', {}):
                segments_with_data.append(seg_name)
                if seg_name == 'all':
                    n_recs = len(seg_data['user_recommendations'][uid]['recommendations'])
        
        result_users.append({
            "id": uid,
            "short_id": uid[:8],
            "n_recommendations": n_recs,
            "available_segments": segments_with_data,
        })
    
    return jsonify({"users": result_users})


@app.route("/api/search")
def search():
    """商品検索（セグメント指定可）"""
    query = request.args.get("q", "").lower().strip()
    segment = get_segment_param()
    limit = int(request.args.get("limit", 24))
    
    if not query:
        return jsonify({"items": []})

    matched = []
    for a in ARTICLES_META.values():
        if not a.get("has_image"):
            continue
        # セグメントフィルタ
        if segment != 'all' and a.get('segment') != segment:
            continue
        haystack = " ".join([
            a.get("name", ""),
            a.get("product_type", ""),
            a.get("product_group", ""),
            a.get("colour", ""),
        ]).lower()
        if query in haystack:
            matched.append(a)
            if len(matched) >= limit:
                break
    return jsonify({"query": query, "segment": segment, "items": matched})


@app.route("/api/articles")
def list_articles():
    """商品一覧（セグメント指定可）"""
    segment = get_segment_param()
    limit = int(request.args.get("limit", 48))
    offset = int(request.args.get("offset", 0))

    items = [
        a for a in ARTICLES_META.values()
        if a.get("has_image") and (segment == 'all' or a.get('segment') == segment)
    ]
    total = len(items)
    items = items[offset:offset + limit]
    return jsonify({"total": total, "offset": offset, "limit": limit, "items": items})


if __name__ == "__main__":
    print()
    print("🚀 サーバー起動: http://localhost:5000")
    print("   - トップページ: http://localhost:5000/")
    print("   - レディース:   http://localhost:5000/?segment=ladies")
    print("   - メンズ:       http://localhost:5000/?segment=men")
    print("   - キッズ:       http://localhost:5000/?segment=kids")
    print()
    app.run(host="0.0.0.0", port=5000, debug=True)
