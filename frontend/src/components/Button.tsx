import classNames from 'classnames';
import { ButtonHTMLAttributes } from 'react';

const variants = {
  primary:
    'bg-primary text-primary-foreground hover:opacity-90 shadow-sm transition-colors border border-primary',
  secondary:
    'bg-surface text-text border border-border hover:bg-muted transition-colors shadow-sm',
  ghost: 'bg-transparent text-text hover:bg-muted border border-transparent',
};

const sizes = {
  md: 'px-4 py-2 text-sm font-medium rounded-lg',
  lg: 'px-5 py-3 text-base font-semibold rounded-xl',
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
};

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={classNames(
        'inline-flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
