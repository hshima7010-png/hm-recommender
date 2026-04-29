# H&M レコメンドECサイト

KaggleのH&M Personalized Fashion RecommendationsデータセットをPython/pandasで分析し、3種類のレコメンドエンジンを実装したECサイト。

## 機能

1. **新規ユーザー向け人気商品**: 全体の購買頻度ランキング + 季節性考慮
2. **あなたへのおすすめ（購買履歴ベース）**: ユーザーベース協調フィルタリング
3. **関連商品（商品ページ用）**: コンテンツベースフィルタリング（カテゴリ・色・価格）

## セットアップ

### 1. 仮想環境の作成と依存関係インストール
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. データのダウンロード
[Kaggle H&M Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data) から以下を `data/` に配置:

```
data/
├── articles.csv                (約36MB)
├── customers.csv               (約200MB)
├── transactions_train.csv      (約3.5GB)
├── sample_submission.csv       (使用しない)
└── images_128_128/             (商品画像フォルダ)
    ├── 010/
    │   ├── 0108775015.jpg
    │   └── ...
    ├── 011/
    └── ...
```

`images_128_128/` 配下は `先頭3桁/article_id.jpg` の構造。
APIサーバーが自動でこのフォルダから画像を配信します。

### 3. データ分析を実行
```bash
# Jupyter Notebookで分析実行
jupyter notebook notebooks/01_eda.ipynb
```

### 4. レコメンド事前計算
```bash
python src/build_recommendations.py
```
→ `output/recommendations.json` が生成される

### 5. APIサーバー起動
```bash
python api/server.py
```
→ http://localhost:5000 でAPI起動

### 6. フロントエンドを開く
ブラウザで http://localhost:5000 にアクセス（APIサーバーがフロントも配信します）

⚠️ **`frontend/index.html` を直接開くのではなく、必ずFlaskサーバー経由で見てください**。
画像とAPIが同一オリジン(localhost:5000)で配信されるため、直接開くと画像とAPIが見られません。

## VS Code推奨拡張機能

- Python
- Pylance
- Jupyter
- Live Server
- Rainbow CSV (CSVファイル可視化)

## 技術スタック

- **データ分析**: Python 3.9+, pandas, numpy, matplotlib, seaborn
- **レコメンド**: scikit-learn, scipy（疎行列）, implicit（オプション）
- **API**: Flask, Flask-CORS
- **フロント**: HTML / CSS / JavaScript（バニラ）
