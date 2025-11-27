import classNames from 'classnames';
import { InputHTMLAttributes } from 'react';

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
};

export function Input({ label, error, className, ...props }: InputProps) {
  return (
    <label className="flex flex-col gap-2 text-sm font-medium text-text">
      {label}
      <input
        className={classNames(
          'rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-primary',
          'transition-colors',
          error ? 'border-red-400 focus:border-red-500' : null,
          className,
        )}
        {...props}
      />
      {error ? <span className="text-xs font-normal text-red-500">{error}</span> : null}
    </label>
  );
}
