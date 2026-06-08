// src/app/components/ImageModal.jsx
// Responsive image modal viewer.
// Sizes: above xl → max 70vw/70vh, below lg → max 85vw/80vh, below md → 95vw/88vh.
// Never expands beyond the viewport. Closed by clicking backdrop or Escape key.

"use client";

import { useEffect, useCallback } from "react";
import { useApp } from "@/app/context/AppContext";

function imgSrc(image) {
  return `/api/image/${image.folder}/${encodeURIComponent(image.name)}`;
}

export default function ImageModal() {
  const { modalImage, closeModal } = useApp();

  const handleKey = useCallback(
    (e) => { if (e.key === "Escape") closeModal(); },
    [closeModal]
  );

  useEffect(() => {
    if (!modalImage) return;
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [modalImage, handleKey]);

  if (!modalImage) return null;

  const folderBadge = {
    input: { label: "Input", cls: "bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200" },
    upscaled: { label: "Upscaled", cls: "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300" },
    enhanced: { label: "Enhanced", cls: "bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300" },
    bg_removed: { label: "BG Removed", cls: "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300" },
  }[modalImage.folder] || { label: modalImage.folder, cls: "bg-slate-200 dark:bg-slate-700" };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={closeModal}
    >
      <div
        className="
          relative flex flex-col
          bg-white dark:bg-slate-900
          rounded-2xl shadow-2xl overflow-hidden
          w-[95vw] max-w-[95vw]
          md:w-auto md:max-w-[85vw]
          xl:max-w-[70vw]
        "
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`px-2 py-0.5 rounded-md text-xs font-semibold ${folderBadge.cls}`}>
              {folderBadge.label}
            </span>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
              {modalImage.name}
            </span>
          </div>
          <button
            onClick={closeModal}
            aria-label="Close"
            className="
              ml-4 shrink-0 w-8 h-8 rounded-full flex items-center justify-center
              bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700
              text-slate-600 dark:text-slate-300 transition-colors
            "
          >
            ✕
          </button>
        </div>

        {/* Image */}
        <div className="flex items-center justify-center p-4 bg-[#f0f0f0] dark:bg-slate-950">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imgSrc(modalImage)}
            alt={modalImage.name}
            className="
              object-contain rounded-lg
              max-h-[60vh] md:max-h-[70vh] xl:max-h-[75vh]
              max-w-full
            "
          />
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700
          flex items-center justify-between text-xs text-slate-400 dark:text-slate-500">
          <span>{modalImage.folder}/{modalImage.name}</span>
          {modalImage.size && (
            <span>{(modalImage.size / 1024).toFixed(0)} KB</span>
          )}
        </div>
      </div>
    </div>
  );
}
