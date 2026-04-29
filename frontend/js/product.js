/**
 * product.html - セグメント対応版
 */

(async function init() {
  await initUserSelector();
  
  // セグメントタブを初期化（クリックでindex.htmlへ移動）
  initSegmentTabs(null);
  
  const params = new URLSearchParams(window.location.search);
  const articleId = params.get('id');
  if (!articleId) {
    document.getElementById('product-detail').innerHTML = 
      '<div class="loading">商品IDが指定されていません</div>';
    return;
  }
  
  await loadProductDetail(articleId);
  await loadRelated(articleId);
  
  const userId = UserState.getCurrentUserId();
  if (userId) {
    // 商品の所属セグメントでユーザー推薦も出す
    const article = await RecommenderAPI.getArticle(articleId).catch(() => null);
    const seg = (article && article.segment && article.segment !== '_other')
      ? article.segment
      : 'all';
    await loadCfRecommendations(userId, seg);
  }
})();


async function loadProductDetail(articleId) {
  try {
    const article = await RecommenderAPI.getArticle(articleId);
    const container = document.getElementById('product-detail');
    
    const priceText = article.price > 0
      ? `¥${Math.round(article.price * 1000).toLocaleString()}`
      : 'お問い合わせください';
    
    const hasImage = article.image_url && article.has_image !== false;
    const imageBlockHtml = hasImage
      ? `<img src="${article.image_url}" alt="${escapeHtml(article.name)}"
             style="width:100%; height:100%; object-fit:cover;"
             onerror="this.outerHTML='<div class=\\'detail-image-fallback\\'><div style=font-size:64px;>👗</div>${escapeHtml(article.product_type)}<br><small>${escapeHtml(article.colour)}</small></div>';">`
      : `<div class="detail-image-fallback">
           <div style="font-size:64px;">👗</div>
           ${escapeHtml(article.product_type)}<br>
           <small>${escapeHtml(article.colour)}</small>
         </div>`;
    
    container.innerHTML = `
      <div class="product-detail-image">
        ${imageBlockHtml}
      </div>
      <div class="product-detail-info">
        <h1>${escapeHtml(article.name || article.product_type)}</h1>
        <div class="meta">${escapeHtml(article.product_group)} · ${escapeHtml(article.index_name)}</div>
        <div class="price">${priceText}</div>
        <p class="description">${escapeHtml(article.description) || '商品説明はありません'}</p>
        
        <div class="attr-row"><div class="label">商品タイプ</div><div>${escapeHtml(article.product_type)}</div></div>
        <div class="attr-row"><div class="label">カラー</div><div>${escapeHtml(article.colour)}</div></div>
        <div class="attr-row"><div class="label">部門</div><div>${escapeHtml(article.department)}</div></div>
        <div class="attr-row"><div class="label">商品ID</div><div style="font-family:monospace;font-size:12px;">${escapeHtml(article.id)}</div></div>
        
        <button class="btn-primary">カートに追加</button>
      </div>
    `;
  } catch (e) {
    console.error(e);
    document.getElementById('product-detail').innerHTML = 
      '<div class="loading">商品が見つかりませんでした</div>';
  }
}


async function loadRelated(articleId) {
  const grid = document.getElementById('related-grid');
  grid.innerHTML = '<div class="loading">関連商品を取得中…</div>';
  
  try {
    const data = await RecommenderAPI.getRelated(articleId);
    if (!data.items || data.items.length === 0) {
      grid.innerHTML = '<div class="loading">関連商品が見つかりませんでした</div>';
    } else {
      renderProductGrid('related-grid', data.items, { tag: '関連' });
    }
  } catch (e) {
    console.error(e);
    grid.innerHTML = '<div class="loading">関連商品の取得に失敗しました</div>';
  }
}


async function loadCfRecommendations(userId, segment) {
  const section = document.getElementById('cf-related');
  section.classList.remove('hidden');
  
  try {
    const data = await RecommenderAPI.getRecommendations(userId, segment);
    if (data.items && data.items.length > 0) {
      renderProductGrid('for-you-grid', data.items.slice(0, 8), {
        tag: 'あなたへ',
      });
    } else {
      section.classList.add('hidden');
    }
  } catch (e) {
    console.error(e);
    section.classList.add('hidden');
  }
}
