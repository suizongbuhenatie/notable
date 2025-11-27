import { PropsWithChildren } from 'react';
import { Button } from '../components/Button';
import { Sidebar, type NavItem } from '../components/Sidebar';
import { useTheme } from '../providers/ThemeProvider';

const defaultNav: NavItem[] = [
  { label: 'Dashboard', href: '#dashboard', icon: '📊', active: true },
  { label: 'Notes', href: '#notes', icon: '📝' },
  { label: 'Tasks', href: '#tasks', icon: '✅' },
  { label: 'Settings', href: '#settings', icon: '⚙️' },
];

export function BaseLayout({ children, navItems = defaultNav }: PropsWithChildren<{ navItems?: NavItem[] }>) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen bg-background text-text">
      <Sidebar
        items={navItems}
        footer={
          <Button variant="secondary" className="w-full" onClick={toggleTheme}>
            Toggle {theme === 'light' ? 'Dark' : 'Light'} Mode
          </Button>
        }
      />
      <main className="flex-1 bg-background px-8 py-6">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-wide text-text-muted">Workspace</p>
            <h1 className="text-2xl font-bold text-text">Welcome to Notable</h1>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="secondary">Invite</Button>
            <Button>New Note</Button>
          </div>
        </header>
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="lg:col-span-2 space-y-4">
            {children}
          </section>
          <aside className="space-y-4">
            <div className="rounded-xl border border-border bg-surface p-4 shadow-card">
              <h3 className="text-lg font-semibold text-text">Quick tips</h3>
              <p className="mt-2 text-sm text-text-muted">
                Use the theme toggle in the sidebar to switch between light and dark palettes.
              </p>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
