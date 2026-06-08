// src/app/context/AppContext.jsx
// Global client-side state for the K9 Crystal Pipeline web app.
// Provides: selected image, modal state, theme, image list, sort order.

"use client";

import { createContext, useContext, useState, useCallback } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [images, setImages] = useState([]);
  const [loadingImages, setLoadingImages] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null); // { name, folder, relativePath, ... }
  const [modalImage, setModalImage] = useState(null);       // image to show in the modal viewer
  const [sortBy, setSortBy] = useState("name");             // "name" | "mtime" | "folder"
  const [sortDir, setSortDir] = useState("asc");
  const [theme, setTheme] = useState("dark");
  const [refreshKey, setRefreshKey] = useState(0);

  const refreshImages = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const openModal = useCallback((image) => setModalImage(image), []);
  const closeModal = useCallback(() => setModalImage(null), []);

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  const sortedImages = [...images].sort((a, b) => {
    let cmp = 0;
    if (sortBy === "name") cmp = a.name.localeCompare(b.name);
    else if (sortBy === "mtime") cmp = new Date(a.mtime) - new Date(b.mtime);
    else if (sortBy === "folder") cmp = a.folder.localeCompare(b.folder) || a.name.localeCompare(b.name);
    return sortDir === "asc" ? cmp : -cmp;
  });

  return (
    <AppContext.Provider
      value={{
        images: sortedImages,
        rawImages: images,
        setImages,
        loadingImages,
        setLoadingImages,
        selectedImage,
        setSelectedImage,
        modalImage,
        openModal,
        closeModal,
        sortBy,
        setSortBy,
        sortDir,
        setSortDir,
        theme,
        toggleTheme,
        refreshKey,
        refreshImages,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
