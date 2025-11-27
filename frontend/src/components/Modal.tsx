import { ReactNode, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Button } from './Button';

type ModalProps = {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
};

export function Modal({ title, open, onClose, children }: ModalProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-surface shadow-card">
        <header className="flex items-center justify-between border-b border-border px-6 py-4">
          <h3 className="text-lg font-semibold text-text">{title}</h3>
          <Button variant="ghost" size="md" aria-label="Close modal" onClick={onClose}>
            ✕
          </Button>
        </header>
        <div className="px-6 py-4 text-text">{children}</div>
        <footer className="flex justify-end gap-3 border-t border-border px-6 py-4">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button>Confirm</Button>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
