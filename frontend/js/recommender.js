/**
 * レコメンダーAPI共通クライアント（セグメント対応版）
 */

const API_BASE = window.location.port === '5000' ? '' : 'http://localhost:5000';
const VALID_SEGMENTS = ['all', 'ladies', 'men', 'kids'];

// ======== セグメント状態管理 ========
const SegmentState = {
  /**
   * 現在のセグメントを取得
   * 優先順位: URLパラメータ > localStorage > デフォルト'all'
   */
  getCurrentSegment() {
    const urlParams = new URLSearchParams(window.location.search);
    const fromUrl = urlParams.get('segment');
    if (fromUrl && VALID_SEGMENTS.includes(fromUrl)) {
      localStorage.setItem('hm_demo_segment', fromUrl);
      return fromUrl;
    }
    const fromStorage = localStorage.getItem('hm_demo_segment');
    if (fromStorage && VALID_SEGMENTS.includes(fromStorage)) {
      return fromStorage;
    }
    return 'all';
  },
  
  setSegment(segment) {
    if (VALID_SEGMENTS.includes(segment)) {
      localStorage.setItem('hm_demo_segment', segment);
    }
  },
  
  /** 現在のページに?segment=XXXを付けたURLを返す */
  buildUrl(segment, basePath = null) {
    const path = basePath || window.location.pathname;
    return `${path}?segment=${segment}`;
  }
};

// ======== ユーザー状態管理 ========
const UserState = {
  getCurrentUserId() {
    return localStorage.getItem('hm_demo_user_id') || '';
  },
  setCurrentUserId(userId) {
    if (userId) {
      localStorage.setItem('hm_demo_user_id', userId);
    } else {
      localStorage.removeItem('hm_demo_user_id');
    }
  },
};

// ======== API通信 ========
const RecommenderAPI = {
  async getPopular(segment = 'all', age = 'overall') {
    const res = await fetch(`${API_BASE}/api/popular?segment=${segment}&age=${age}`);
    if (!res.ok) throw new Error('Failed to fetch popular');
    return res.json();
  },

  async getRelated(articleId) {
    const res = await fetch(`${API_BASE}/api/related/${articleId}`);
    if (!res.ok) throw new Error('Failed to fetch related');
    return res.json();
  },

  async getRecommendations(customerId, segment = 'all') {
    const res = await fetch(`${API_BASE}/api/recommend/${customerId}?segment=${segment}`);
    if (!res.ok) throw new Error('Failed to fetch recommendations');
    return res.json();
  },

  async getArticle(articleId) {
    const res = await fetch(`${API_BASE}/api/article/${articleId}`);
    if (!res.ok) throw new Error('Article not found');
    return res.json();
  },

  async search(query, segment = 'all') {
    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&segment=${segment}`);
    if (!res.ok) throw new Error('Search failed');
    return res.json();
  },

  async getSampleUsers() {
    const res = await fetch(`${API_BASE}/api/sample-users`);
    if (!res.ok) throw new Error('Failed to fetch sample users');
    return res.json();
  },
  
  async getSegmentInfo() {
    const res = await fetch(`${API_BASE}/api/segment-info`);
    if (!res.ok) throw new Error('Failed to fetch segment info');
    return res.json();
  },
};

// ======== 商品カードのレンダリング ========
function renderProductCard(article, options = {}) {
  const { tag = null, onclick = null } = options;

  const card = document.createElement('a');
  card.href = `product.html?id=${article.id}`;
  card.className = 'product-card';
  if (onclick) {
    card.addEventListener('click', (e) => {
      e.preventDefault();
      onclick(article);
    });
  }

  const priceText = article.price > 0 ? `¥${Math.round(article.price * 1000)}` : '';
  const tagHtml = tag ? `<div class="product-card-tag">${tag}</div>` : '';

  const hasImage = article.image_url && article.has_image !== false;
  const imageHtml = hasImage
    ? `<img src="${article.image_url}" alt="${escapeHtml(article.name)}" loading="lazy"
           onerror="this.style.display='none'; this.parentElement.querySelector('.product-card-image-fallback').style.display='flex';">
       <div class="product-card-image-fallback" style="display:none;">
         <div class="fallback-icon">👗</div>
         <div class="fallback-text">${escapeHtml(article.product_type)}</div>
         <div class="fallback-color">${escapeHtml(article.colour)}</div>
       </div>`
    : `<div class="product-card-image-fallback" style="display:flex;">
         <div class="fallback-icon">👗</div>
         <div class="fallback-text">${escapeHtml(article.product_type)}</div>
         <div class="fallback-color">${escapeHtml(article.colour)}</div>
       </div>`;

  card.innerHTML = `
    <div class="product-card-image">
      ${tagHtml}
      ${imageHtml}
    </div>
    <div class="product-card-name">${escapeHtml(article.name || article.product_type)}</div>
    <div class="product-card-meta">${escapeHtml(article.colour)} · ${escapeHtml(article.product_type)}</div>
    <div class="product-card-price">${priceText}</div>
  `;
  return card;
}

function renderProductGrid(containerId, articles, options = {}) {
  const grid = document.getElementById(containerId);
  if (!grid) return;
  grid.innerHTML = '';
  if (!articles || articles.length === 0) {
    grid.innerHTML = '<div class="loading">商品が見つかりませんでした</div>';
    return;
  }
  articles.forEach((a, i) => {
    grid.appendChild(renderProductCard(a, {
      ...options,
      tag: options.tagFn ? options.tagFn(a, i) : options.tag,
    }));
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ======== セグメントタブの初期化 ========
/**
 * セグメントタブをセットアップ
 * @param {function} onChange - セグメント変更時のコールバック (segment) => {}
 */
function initSegmentTabs(onChange) {
  const currentSegment = SegmentState.getCurrentSegment();
  const tabs = document.querySelectorAll('.segment-tab');
  
  tabs.forEach(tab => {
    const seg = tab.getAttribute('data-segment');
    if (seg === currentSegment) {
      tab.classList.add('active');
    }
    
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      const newSeg = tab.getAttribute('data-segment');
      
      // タブのアクティブ状態を切り替え
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      
      // 状態保存
      SegmentState.setSegment(newSeg);
      
      // URLにも反映（リロードなし）
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.set('segment', newSeg);
      window.history.replaceState({}, '', newUrl);
      
      if (onChange) onChange(newSeg);
    });
  });
}

// ======== ユーザーセレクタの初期化 ========
async function initUserSelector() {
  const selector = document.getElementById('user-selector');
  if (!selector) return;

  try {
    const data = await RecommenderAPI.getSampleUsers();
    data.users.forEach(u => {
      const opt = document.createElement('option');
      opt.value = u.id;
      opt.textContent = `User: ${u.short_id}… (${u.n_recommendations}件)`;
      selector.appendChild(opt);
    });
    
    selector.value = UserState.getCurrentUserId() || '';
    selector.addEventListener('change', (e) => {
      UserState.setCurrentUserId(e.target.value);
      window.location.reload();
    });
  } catch (e) {
    console.warn('Failed to load sample users:', e);
  }
}

// ======== 検索バー ========
function initSearchBar(onSearch) {
  const input = document.getElementById('search-input');
  if (!input) return;
  
  let debounceTimer;
  input.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const q = e.target.value.trim();
      if (q.length >= 2) {
        if (onSearch) onSearch(q);
      } else if (q.length === 0) {
        if (onSearch) onSearch('');
      }
    }, 300);
  });
}
