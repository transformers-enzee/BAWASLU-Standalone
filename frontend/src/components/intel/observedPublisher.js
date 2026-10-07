export function observedPublisherFromUrl(value) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) return { platform: '', handle: '' };
    const host = url.hostname.toLowerCase().replace(/^www\./, '');
    const segments = url.pathname.split('/').filter(Boolean).map(decodeURIComponent);
    const videoPost = /^@[^/]+$/.test(segments[0] || '') && segments[1] === 'video' && segments[2];
    const photoPost = !url.username && !url.password && /^\/(@[A-Za-z0-9._]{1,24})\/photo\/\d+\/?$/.test(url.pathname);
    if ((host === 'tiktok.com' || host.endsWith('.tiktok.com')) && (videoPost || photoPost)) {
      return { platform: 'TikTok', handle: segments[0] };
    }
    if (['x.com', 'twitter.com'].some(domain => host === domain || host.endsWith('.' + domain)) && segments[0] && segments[1]?.toLowerCase() === 'status' && segments[2]) {
      return { platform: 'X', handle: segments[0] };
    }
  } catch { /* URL still being entered */ }
  return { platform: '', handle: '' };
}