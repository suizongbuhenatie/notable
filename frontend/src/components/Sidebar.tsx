import classNames from 'classnames';
import { ReactNode } from 'react';

export type NavItem = {
  label: string;
  href: string;
  icon?: string;
  active?: boolean;
};

type SidebarProps = {
  items: NavItem[];
  footer?: ReactNode;
};

export function Sidebar({ items, footer }: SidebarProps) {
  return (
    <aside className="flex h-full w-64 flex-col gap-4 border-r border-border bg-surface p-4">
      <div className="text-lg font-bold text-text">Notable</div>
      <nav className="flex-1 space-y-1">
        {items.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className={classNames(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              item.active ? 'bg-primary text-primary-foreground' : 'hover:bg-muted text-text',
            )}
          >
            {item.icon ? <span className="text-lg">{item.icon}</span> : null}
            {item.label}
          </a>
        ))}
      </nav>
      {footer}
    </aside>
  );
}
