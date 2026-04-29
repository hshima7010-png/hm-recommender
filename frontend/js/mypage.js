/**
 * mypage.html - セグメント対応版
 */

(async function init() {
  await initUserSelector();
  
  // セグメントタブ初期化（変更時にレコメンド再読込）
  initSegmentTabs(async () => {
    await loadUserContent();
  });
  
  await loadUserContent();
})();


async function loadUserContent() {
  const userId = UserState.getCurrentUserId();
  const segment = SegmentState.getCurrentSegment();
  
  const greeting = document.getElementById('user-greeting');
  const userIdDisplay = document.getElementById('user-id-display');
  const loginPrompt = document.getElementById('login-prompt');
  const section = document.getElementById('for-you');
  
  if (!userId) {
    greeting.textContent = 'ゲストとしてログイン中';
    userIdDisplay.textContent = '';
    loginPrompt.classList.remove('hidden');
    section.classList.add('hidden');
    return;
  }
  
  greeting.textContent = `ようこそ、お客様`;
  userIdDisplay.textContent = `Customer ID: ${userId.substring(0, 16)}…  /  カテゴリ: ${getSegmentLabel(segment)}`;
  loginPrompt.classList.add('hidden');
  
  section.classList.remove('hidden');
  
  const grid = document.getElementById('for-you-grid');
  grid.innerHTML = '<div class="loading">レコメンドを計算中…</div>';
  
  try {
    const data = await RecommenderAPI.getRecommendations(userId, segment);
    
    const sourceTag = document.getElementById('for-you-source');
    if (data.source === 'collaborative_filtering') {
      sourceTag.textContent = `協調FL (${getSegmentLabel(segment)})`;
    } else {
      sourceTag.textContent = '人気度ベース（コールドスタート）';
    }
    
    if (!data.items || data.items.length === 0) {
      grid.innerHTML = `<div class="loading">${getSegmentLabel(segment)}カテゴリでのレコメンドがありません。<br>別のカテゴリをお試しください。</div>`;
    } else {
      renderProductGrid('for-you-grid', data.items, { tag: 'あなたへ' });
    }
  } catch (e) {
    console.error(e);
    grid.innerHTML = '<div class="loading">レコメンドの取得に失敗しました</div>';
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
