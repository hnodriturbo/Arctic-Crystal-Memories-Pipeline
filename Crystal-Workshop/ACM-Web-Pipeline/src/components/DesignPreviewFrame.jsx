"use client";
/** Purpose: Fit the complete authored design viewport into the preview without cropping or changing its layout. */
import { useEffect, useRef, useState } from 'react';

/** Observe the available frame, including after its previously hidden workspace becomes visible. */
export default function DesignPreviewFrame({ preview }) {
  const frame = useRef(null);
  const [scale, setScale] = useState(0);
  const width = Number(preview.width) || 1920;
  const height = Number(preview.height) || 1080;
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      setScale(Math.min(entry.contentRect.width / width, entry.contentRect.height / height));
    });
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, [width, height]);
  return <div ref={frame} className="relative w-full overflow-hidden rounded-lg border border-surface-border bg-black" style={{ height: 'min(65vh, 680px)' }}>
    <iframe key={preview.rootRel} title={preview.name}
      src={'/api/claude-design/preview/' + preview.rootRel.split('/').map(encodeURIComponent).join('/')}
      width={width} height={height} className="absolute left-1/2 top-1/2 border-0"
      style={{ width, height, maxWidth: 'none', transform: 'translate(-50%, -50%) scale(' + scale + ')', transformOrigin: 'center', visibility: scale > 0 ? 'visible' : 'hidden' }} />
  </div>;
}
