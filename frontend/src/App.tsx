import { useState } from 'react';
import { Button } from './components/Button';
import { Input } from './components/Input';
import { Modal } from './components/Modal';
import { BaseLayout } from './layouts/BaseLayout';
import { ThemeProvider } from './providers/ThemeProvider';

export default function App() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <ThemeProvider>
      <BaseLayout>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
            <h2 className="text-lg font-semibold text-text">Create a note</h2>
            <p className="mt-1 text-sm text-text-muted">
              Capture thoughts quickly with reusable inputs and buttons.
            </p>
            <div className="mt-4 space-y-3">
              <Input label="Title" placeholder="Meeting notes" />
              <Input label="Tags" placeholder="Productivity, Planning" />
              <Button className="w-full" onClick={() => setModalOpen(true)}>
                Save draft
              </Button>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
            <h2 className="text-lg font-semibold text-text">Shared components</h2>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              <li>• Tailwind-powered base layout with responsive spacing.</li>
              <li>• Light and dark palettes driven by CSS variables.</li>
              <li>• Buttons, inputs, modals, and sidebars ready to reuse.</li>
            </ul>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button>Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
            </div>
          </div>
        </div>

        <Modal title="Save draft" open={modalOpen} onClose={() => setModalOpen(false)}>
          <p className="text-text-muted">
            This modal reuses the shared Button component and respects the active theme.
          </p>
        </Modal>
      </BaseLayout>
    </ThemeProvider>
  );
}
