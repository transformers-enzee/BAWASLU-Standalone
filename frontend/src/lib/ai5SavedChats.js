/**
 * Saved-chat navigation is deliberately simple: show every conversation for
 * libraries of 0–3, and only expose the expanded/search state for 4+.
 * Shared by the AI-5 UI and executable regression tests.
 */
export const RECENT_CHAT_LIMIT = 3;

export function canExpandSavedChats(count) {
  return Number.isInteger(count) && count > RECENT_CHAT_LIMIT;
}

export function savedChatsForDisplay(chats, expanded = false, search = '') {
  const all = Array.isArray(chats) ? chats : [];
  if (!expanded || !canExpandSavedChats(all.length)) {
    return all.slice(0, RECENT_CHAT_LIMIT);
  }
  const query = String(search || '').trim().toLocaleLowerCase();
  return query
    ? all.filter(chat => String(chat?.title || '').toLocaleLowerCase().includes(query))
    : all;
}
