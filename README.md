# H&M Personalized Recommender EC

KaggleのH&M Personalized Fashion Recommendationsデータセットを活用した、レコメンド特化型ECサイトのデモプロジェクト。

3種類の異なるレコメンドアルゴリズムを実装し、性別セグメント別に独立して学習・配信する構成。

![Tech](https://img.shields.io/badge/Python-3.11+-blue) ![pandas](https://img.shields.io/badge/pandas-2.x-orange) ![scikit-learn](https://img.shields.io/badge/scikit--learn-1.x-yellow) ![Flask](https://img.shields.io/badge/Flask-3.x-green)

---

## ✨ 特徴

### 3種類のレコメンドエンジン

| エンジン | アルゴリズム | 表示場所 |
|---|---|---|
| **新規ユーザー向け人気商品** | 時間減衰重み付き集計 + カテゴリ多様化 | トップ・年齢別タブ |
| **あなたへのおすすめ** | Item-Item協調フィルタリング (scipy疎行列 + コサイン類似度) | マイページ・トップ |
| **関連商品** | コンテンツベース (重み付きOne-Hot + コサイン類似度) | 商品詳細ページ |

### 性別セグメント対応

`LADIES / MEN / KIDS` の各カテゴリで独立してレコメンドを学習・配信。
ユーザーが選択したカテゴリに応じたパーソナライズ結果を表示。

### 画像のある商品のみを厳選

データセット中、画像が用意された商品のみを学習対象とすることで、ECサイトとしての見栄えを担保。

---

## 🛠 技術スタック

**データ分析・機械学習**
- Python 3.11+
- pandas / numpy（データ処理）
- scikit-learn（特徴量エンコーディング、類似度計算）
- scipy（疎行列演算）

**バックエンド**
- Flask（軽量APIサーバー）
- Flask-CORS

**フロントエンド**
- HTML / CSS / Vanilla JavaScript
- レスポンシブデザイン

---

## 📂 プロジェクト構成

```
hm-recommender/
├── data/                        # データ配置場所（.gitignore対象）
├── notebooks/
│   └── 01_eda.ipynb            # 探索的データ分析
├── src/
│   ├── data_loader.py          # メモリ効率を考慮したデータ読み込み
│   ├── analysis.py             # EDAヘルパー関数
│   ├── recommenders/
│   │   ├── popularity.py       # 人気商品レコメンダー
│   │   ├── collaborative.py    # 協調フィルタリング
│   │   └── content_based.py    # コンテンツベース
│   └── build_recommendations.py  # レコメンド事前計算スクリプト
├── api/
│   └── server.py               # Flask APIサーバー
├── frontend/
│   ├── index.html              # トップページ
│   ├── product.html            # 商品詳細
│   ├── mypage.html             # マイページ
│   ├── css/style.css
│   └── js/
└── output/                     # 事前計算結果（.gitignore対象）
```

---

## 🚀 セットアップ手順

### 前提条件

- Python 3.11以上
- KaggleアカウントとH&Mデータセット（後述）

### 1. リポジトリのクローン

```bash
git clone https://github.com/<your-username>/hm-recommender.git
cd hm-recommender
```

### 2. 仮想環境とパッケージインストール

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Kaggleデータの配置

[Kaggle H&M Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data) からデータをダウンロードし、以下のように配置:

```
data/
├── articles.csv                (約36MB)
├── customers.csv               (約200MB)
├── transactions_train.csv      (約3.5GB)
└── images_128_128/
    ├── 010/
    │   ├── 0108775015.jpg
    │   └── ...
    ├── 011/
    └── ...
```

> **注**: データセットの容量が大きいため、初回ダウンロードには時間がかかります。

### 4. レコメンドの事前計算

```bash
python src/build_recommendations.py
```

データ規模に応じて 5〜15 分程度かかります。`output/recommendations.json` などが生成されます。

### 5. APIサーバー起動

```bash
python api/server.py
```

ブラウザで [http://localhost:5000](http://localhost:5000) にアクセス。

---

## 🧠 アルゴリズム詳細

### 1. 人気商品レコメンダー（Popularity-based）

直近2週間の購買履歴から、時間減衰重み（半減期1週間の指数関数）を適用して人気度を算出。

```python
weight = exp(-days_ago / 7)
score(item) = sum(weight for each purchase)
```

カテゴリ間でラウンドロビン抽出することで多様性を確保。

### 2. 協調フィルタリング（Item-Item Collaborative Filtering）

User-Item インタラクション行列 (scipy疎行列) からItem-Item類似度を算出:

```
item_similarity = normalize(item_vectors) @ normalize(item_vectors).T
```

ユーザーの購買履歴から類似商品を集約してスコアリング。

- **対象**: 直近90日のトランザクション
- **フィルタ**: 5回以上購入された商品のみ

### 3. コンテンツベースフィルタリング

商品属性のOne-Hotベクトルを重み付けして特徴量化:

| 属性 | 重み |
|---|---|
| 商品タイプ (T-shirt, Dressなど) | × 3.0 |
| 商品グループ | × 2.0 |
| ターゲット層 (Ladies/Mensなど) | × 1.5 |
| ガーメントグループ | × 1.5 |
| 色 | × 1.5 |
| その他 | × 1.0 |

L2正規化後、コサイン類似度で類似商品を抽出。

---

## 📊 データ分析（EDA）

`notebooks/01_eda.ipynb` で以下を実施:

- 商品カテゴリ・色の分布
- 顧客の年齢分布・会員ステータス
- 日次・曜日別の売上トレンド
- カテゴリ別の価格分布
- 月別×カテゴリの季節性パターン
- RFM風の顧客セグメンテーション

---

## ⚙️ パラメータ調整

`src/build_recommendations.py` の最上部で各種パラメータを調整可能:

```python
TRANSACTION_SAMPLE_FRAC = 0.05  # サンプリング比率（0.05〜1.0）
TOP_USERS_PER_SEGMENT = 3000    # 事前計算するユーザー数
TOP_ARTICLES_FOR_RELATED_PER_SEGMENT = 1500  # 関連商品の対象商品数
```

---

## 📝 ライセンス

このプロジェクトのコードは MIT License です。

ただし、H&M Personalized Fashion Recommendationsデータセットは [Kaggleのコンペティションルール](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/rules) に従う必要があります。再配布は禁止されているため、データは各自Kaggleからダウンロードしてください。

---

## 🙋 作者

- GitHub: [@Shima0710](https://github.com/Shima0710)
