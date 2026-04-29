/**
 * index.html (トップページ) - セグメント対応版
 */

let currentAge = 'overall';

(async function init() {
  await initUserSelector();
  
  // セグメントタブを初期化（変更時はページ全体を再読込）
  initSegmentTabs(async (newSegment) => {
    await loadAll();
  });
  
  await loadAll();
  
  setupAgeTabs();
  initSearchBar(handleSearch);
})();


async function loadAll() {
  const segment = SegmentState.getCurrentSegment();
  const userId = UserState.getCurrentUserId();
  
  // 「あなたへのおすすめ」（ログイン時のみ）
  if (userId) {
    await loadForYou(userId, segment);
  } else {
    document.getElementById('for-you').classList.add('hidden');
  }
  
  // 人気商品
  await loadPopular(segment, currentAge);
  
  // セクションタイトル更新
  updateSectionTitles(segment);
}


function updateSectionTitles(segment) {
  const titles = {
    'all': '今週の人気アイテム',
    'ladies': 'レディースの人気アイテム',
    'men': 'メンズの人気アイテム',
    'kids': 'キッズの人気アイテム',
  };
  const popularTitle = document.getElementById('popular-title');
  if (popularTitle) {
    popularTitle.textContent = titles[segment] || titles['all'];
  }
}


async function loadForYou(userId, segment) {
  const section = document.getElementById('for-you');
  section.classList.remove('hidden');
  
  const grid = document.getElementById('for-you-grid');
  grid.innerHTML = '<div class="loading">あなた向けのおすすめを取得中…</div>';
  
  try {
    const data = await RecommenderAPI.getRecommendations(userId, segment);
    
    const sourceTag = document.getElementById('for-you-source');
    const desc = document.getElementById('for-you-desc');
    if (data.source === 'collaborative_filtering') {
      sourceTag.textContent = '協調フィルタリング';
      const segLabel = segment === 'all' ? '' : `（${getSegmentLabel(segment)}）`;
      desc.textContent = `あなたの購買履歴をもとに、似たお客様に人気のアイテムをお届けします${segLabel}`;
    } else {
      sourceTag.textContent = '人気度ベース';
      desc.textContent = data.message || '初めての方にも分かりやすい人気アイテムをご案内';
    }
    
    if (data.items.length === 0) {
      grid.innerHTML = `<div class="loading">${getSegmentLabel(segment)}カテゴリでのレコメンドが見つかりませんでした。<br>別のカテゴリをお試しください。</div>`;
    } else {
      renderProductGrid('for-you-grid', data.items, { tag: 'おすすめ' });
    }
  } catch (e) {
    console.error(e);
    grid.innerHTML = '<div class="loading">レコメンドの取得に失敗しました</div>';
  }
}


async function loadPopular(segment, age) {
  const grid = document.getElementById('popular-grid');
  grid.innerHTML = '<div class="loading">人気商品を取得中…</div>';
  
  try {
    const data = await RecommenderAPI.getPopular(segment, age);
    if (data.items.length === 0) {
      grid.innerHTML = `<div class="loading">${getSegmentLabel(segment)}の人気商品が見つかりませんでした</div>`;
    } else {
      renderProductGrid('popular-grid', data.items, {
        tagFn: (_, i) => i < 3 ? `TOP ${i + 1}` : null,
      });
    }
  } catch (e) {
    console.error(e);
    grid.innerHTML = '<div class="loading">人気商品の取得に失敗しました</div>';
  }
}


function setupAgeTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', async () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentAge = tab.getAttribute('data-age');
      const segment = SegmentState.getCurrentSegment();
      await loadPopular(segment, currentAge);
    });
  });
}


async function handleSearch(query) {
  const section = document.getElementById('search-section');
  
  if (!query) {
    section.classList.add('hidden');
    return;
  }
  
  section.classList.remove('hidden');
  document.getElementById('search-query').textContent = query;
  
  const grid = document.getElementById('search-grid');
  grid.innerHTML = '<div class="loading">検索中…</div>';
  
  try {
    const segment = SegmentState.getCurrentSegment();
    const data = await RecommenderAPI.search(query, segment);
    if (data.items.length === 0) {
      grid.innerHTML = '<div class="loading">検索結果がありませんでした</div>';
    } else {
      renderProductGrid('search-grid', data.items);
    }
    section.scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    console.error(e);
    grid.innerHTML = '<div class="loading">検索に失敗しました</div>';
  }
}


function getSegmentLabel(segment) {
  return {
    'all': '全カテゴリ',
    'ladies': 'レディース',
    'men': 'メンズ',
    'kids': 'キッズ',
  }[segment] || '';
}
