// =============================================================================
// SERV.O v8.1 - PDF MODAL COMPONENT (DRAGGABLE)
// =============================================================================

import React, { useState, useRef, useEffect } from 'react';
import { getApiBaseUrl } from '../../api';

export default function PdfModal({ pdfFile, onClose }) {
  // Costruisci URL completo per il PDF
  const pdfUrl = `${getApiBaseUrl()}/api/v1/upload/pdf/${encodeURIComponent(pdfFile || '')}`;
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const modalRef = useRef(null);

  // Handle mouse down on header to start dragging
  const handleMouseDown = (e) => {
    // Only drag from header, not from buttons
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'A') return;

    setIsDragging(true);
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  // Handle mouse move while dragging
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isDragging) return;

      const newX = e.clientX - dragStart.x;
      const newY = e.clientY - dragStart.y;

      setPosition({ x: newX, y: newY });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragStart]);

  // Reset position when modal opens
  useEffect(() => {
    setPosition({ x: 0, y: 0 });
  }, [pdfFile]);

  if (!pdfFile) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div
        ref={modalRef}
        className="bg-white rounded-lg w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl"
        style={{
          transform: `translate(${position.x}px, ${position.y}px)`,
          cursor: isDragging ? 'grabbing' : 'default'
        }}
      >
        {/* Header trascinabile */}
        <div
          className="flex items-center justify-between p-4 border-b bg-slate-50 rounded-t-lg select-none"
          onMouseDown={handleMouseDown}
          style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-xs">drag</span>
            <h3 className="text-lg font-semibold">{pdfFile}</h3>
          </div>
          <div className="flex gap-2">
            <a
              href={pdfUrl}
              download
              className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
            >
              Scarica
            </a>
            <button
              onClick={onClose}
              className="px-3 py-1 bg-slate-100 text-slate-700 rounded hover:bg-slate-200 text-sm"
            >
              X Chiudi
            </button>
          </div>
        </div>
        {/* Contenuto PDF */}
        <div className="flex-1 p-2 overflow-hidden">
          <iframe
            src={pdfUrl}
            className="w-full h-full rounded border"
            title="PDF Ordine"
          />
        </div>
      </div>
    </div>
  );
}
