// src/app/components/ImageGrid.jsx
// Displays pipeline images as a thumbnail grid with sort controls.
// Single click = select image; double click = open modal.
// Shows upscale-recommended badge when image is from input and has long edge < threshold.

"use client";

import { useState, useEffect } from "react";
import { useApp } from "@/app/context/AppContext";
import { useRouter } from "next/navigation";

const SORT_OPTIONS = [
  { value: "name|asc",   label: "Name A–Z" },
  { value: "name|desc",  label: "Name Z–A" },
  { value: "mtime|desc", label: "Newest first" },
  { value: "mtime|asc",  label: "Oldest first" },
  { value: "folder|asc", label: "Folder" },
];

function imgSrc(image) {
  return `/api/image/${image.folder}/${encodeURIComponent(image.name)}`;
}

function SizeTag({ image }) {
  const [small, setSmall] = useState(false);

  useEffect(() => {
    if (image.folder !== "input" || !image.threshold) return;
    const img = new Image();
    img.onload = () => {
      if (Math.max(img.naturalWidth, img.naturalHeight) < image.threshold) {
        setSmall(true);
      }
    };
    img.src = imgSrc(image);
  }, [image]);

  if (!small) return null;

  return (
    <span className="absolute top-1.5 right-1.5 z-10 px-1.5 py-0.5 rounded text-[10px] font-semibold
      bg-amber-400 text-amber-900 shadow">
      ↑ upscale
    </span>
  );
}

export default function ImageGrid({ folder }) {
  const {
    images, loadingImages, selectedImage, setSelectedImage,
    openModal, sortBy, setSortBy, sortDir, setSortDir,
    refreshKey, setImages, setLoadingImages,
  } = useApp();

  const router = useRouter();

  useEffect(() => {
    setLoadingImages(true);
    fetch("/api/images")
      .then((r) => r.json())
      .then(({ files }) => { setImages(files || []); setLoadingImages(false); })
      .catch(() => setLoadingImages(false));
  }, [refreshKey, setImages, setLoadingImages]);

  const visible = folder === "all"
    ? images
    : images.filter((f) => f.folder === folder);

  function handleSortChange(e) {
    const [col, dir] = e.target.value.split("|");
    setSortBy(col);
    setSortDir(dir);
  }

  const sortValue = `${sortBy}|${sortDir}`;

  function handleClick(img) {
    if (selectedImage?.relativePath === img.relativePath) {
      // second click on same → open modal
      openModal(img);
    } else {
      setSelectedImage(img);
    }
  }

  function handleDblClick(img) {
    openModal(img);
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Sort bar */}
      <div className="flex items-center gap-3">
        <label className="text-sm text-slate-500 dark:text-slate-400 shrink-0">Sort:</label>
        <select
          value={sortValue}
          onChange={handleSortChange}
          className="
            text-sm rounded-lg px-3 py-1.5
            bg-white dark:bg-slate-800
            border border-slate-300 dark:border-slate-600
            text-slate-700 dark:text-slate-200
            focus:outline-none focus:ring-2 focus:ring-indigo-500
          "
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">
          {visible.length} image{visible.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Grid */}
      {loadingImages ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="py-20 text-center text-slate-400 dark:text-slate-500">
          No images found in this folder.
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {visible.map((img) => {
            const isSelected = selectedImage?.relativePath === img.relativePath;
            return (
              <button
                key={img.relativePath}
                onClick={() => handleClick(img)}
                onDoubleClick={() => handleDblClick(img)}
                className={`
                  group relative aspect-square rounded-xl overflow-hidden
                  border-2 transition-all duration-150 text-left
                  focus:outline-none focus:ring-2 focus:ring-indigo-500
                  ${isSelected
                    ? "border-indigo-500 shadow-lg shadow-indigo-500/20 scale-[1.02]"
                    : "border-transparent hover:border-slate-300 dark:hover:border-slate-600"}
                `}
              >
                <SizeTag image={img} />
                {/* Folder badge */}
                <span className="absolute bottom-1.5 left-1.5 z-10 px-1.5 py-0.5 rounded text-[10px]
                  font-medium bg-black/50 text-white backdrop-blur-sm">
                  {img.folder}
                </span>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={imgSrc(img)}
                  alt={img.name}
                  className="w-full h-full object-cover bg-slate-100 dark:bg-slate-800
                    group-hover:scale-105 transition-transform duration-300"
                />
                {isSelected && (
                  <div className="absolute inset-0 bg-indigo-600/10 flex items-center justify-center">
                    <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center">
                      <span className="text-white text-xs">✓</span>
                    </div>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Process button — appears when image is selected */}
      {selectedImage && (
        <div className="sticky bottom-4 flex justify-center">
          <button
            onClick={() => router.push(`/process?file=${encodeURIComponent(selectedImage.name)}&folder=${selectedImage.folder}`)}
            className="
              px-6 py-3 rounded-xl font-semibold text-white
              bg-indigo-600 hover:bg-indigo-700 active:scale-95
              shadow-lg shadow-indigo-600/30
              transition-all duration-150
            "
          >
            Process: {selectedImage.name} →
          </button>
        </div>
      )}
    </div>
  );
}
