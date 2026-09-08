import { motion, AnimatePresence } from "framer-motion";
import { type ReactNode, useEffect, useRef } from "react";
import { useCountUp, formatMetric } from "../hooks/useCountUp";

/* ---------------------------------------------------------------- Button */
type ButtonVariant = "primary" | "ghost" | "outline" | "danger" | "success" | "subtle";

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: "bg-accent text-ink hover:bg-accent-soft font-semibold glow-cyan",
  ghost: "bg-transparent text-fg-dim hover:text-fg hover:bg-panel-2",
  outline: "border border-line text-fg hover:border-accent hover:text-accent bg-transparent",
  danger: "bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25",
  success: "bg-good/15 text-good border border-good/30 hover:bg-good/25",
  subtle: "bg-panel-2 text-fg-dim hover:text-fg hover:bg-line",
};

export function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled,
  className = "",
  title,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: ButtonVariant;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  className?: string;
  title?: string;
  type?: "button" | "submit";
}) {
  const sizes = { sm: "px-2.5 py-1.5 text-xs rounded-lg", md: "px-4 py-2 text-sm rounded-xl", lg: "px-6 py-3 text-base rounded-xl" };
  return (
    <button
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 transition-all duration-200 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none ${BUTTON_STYLES[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  );
}

/* ---------------------------------------------------------------- Card */
export function Card({ children, className = "", pad = true }: { children: ReactNode; className?: string; pad?: boolean }) {
  return <div className={`glass rounded-2xl ${pad ? "p-5" : ""} ${className}`}>{children}</div>;
}

export function SectionTitle({ children, sub, right }: { children: ReactNode; sub?: string; right?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight text-fg">{children}</h2>
        {sub && <p className="text-xs text-fg-faint mt-0.5">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

/* ---------------------------------------------------------------- Badge */
const BADGE_KINDS: Record<string, string> = {
  INFO: "bg-accent/10 text-accent border-accent/25",
  WARNING: "bg-warn/10 text-warn border-warn/25",
  CRITICAL: "bg-danger/10 text-danger border-danger/25",
  success: "bg-good/10 text-good border-good/25",
  default: "bg-panel-2 text-fg-dim border-line",
  baseline: "bg-warn/10 text-warn border-warn/20",
  urbanrelay: "bg-good/10 text-good border-good/20",
  PENDING: "bg-warn/10 text-warn border-warn/20",
  DELIVERED: "bg-good/10 text-good border-good/20",
  IDLE: "bg-panel-2 text-fg-dim border-line",
};

export function Badge({ kind = "default", children }: { kind?: string; children: ReactNode }) {
  const cls = BADGE_KINDS[kind] ?? BADGE_KINDS.default;
  return <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium border ${cls}`}>{children}</span>;
}

export function StatusDot({ color, pulse }: { color: string; pulse?: boolean }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${pulse ? "animate-pulse-soft" : ""}`} style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
  );
}

/* ---------------------------------------------------------------- MetricCard */
const MODE_COLORS: Record<string, string> = {
  baseline: "#f59e0b",
  urbanrelay: "#34d399",
};

export function MetricCard({
  label,
  value,
  decimals = 0,
  suffix = "",
  delta,
  deltaGood = true,
  icon,
  accent = "#38bdf8",
}: {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
  delta?: number | null;
  deltaGood?: boolean;
  icon?: ReactNode;
  accent?: string;
}) {
  const animated = useCountUp(value);
  const showDelta = delta !== undefined && delta !== null && Math.abs(delta) > 0.001;
  const deltaPositive = (delta ?? 0) >= 0;
  const good = deltaPositive === deltaGood;
  return (
    <Card className="relative overflow-hidden !p-4 min-w-[150px]">
      <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: `linear-gradient(90deg, transparent, ${accent}, transparent)` }} />
      <div className="flex items-center gap-1.5 text-fg-faint text-[10px] uppercase tracking-wide leading-tight">
        {icon && <span className="shrink-0 text-[13px]">{icon}</span>}
        <span title={label}>{label}</span>
      </div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold tabular-nums tracking-tight text-fg">{formatMetric(animated, decimals)}</span>
        {suffix && <span className="text-xs text-fg-dim">{suffix}</span>}
      </div>
      {showDelta && (
        <span className={`text-[11px] font-medium ${good ? "text-good" : "text-danger"}`}>
          {deltaPositive ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}
          {suffix ? ` ${suffix}` : ""} vs before
        </span>
      )}
    </Card>
  );
}

/* ---------------------------------------------------------------- Progress */
export function ProgressBar({ value, color = "#38bdf8", className = "" }: { value: number; color?: string; className?: string }) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <div className={`h-1.5 rounded-full bg-panel-2 overflow-hidden ${className}`}>
      <motion.div
        className="h-full rounded-full"
        animate={{ width: `${v * 100}%` }}
        transition={{ type: "spring", stiffness: 120, damping: 20 }}
        style={{ background: `linear-gradient(90deg, ${color}88, ${color})` }}
      />
    </div>
  );
}

/* ---------------------------------------------------------------- Skeleton / Spinner / Empty */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-panel-2 ${className}`} />;
}

export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <span
      className="inline-block rounded-full border-2 border-line border-t-accent animate-spin"
      style={{ width: size, height: size }}
    />
  );
}

export function EmptyState({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center">
      <div className="text-3xl mb-3 opacity-50">◌</div>
      <div className="text-sm text-fg-dim font-medium">{title}</div>
      {sub && <div className="text-xs text-fg-faint mt-1 max-w-sm">{sub}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- Modal */
export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[1200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className={`glass rounded-2xl w-full ${wide ? "max-w-3xl" : "max-w-md"} max-h-[86vh] overflow-y-auto`}
            initial={{ scale: 0.96, y: 12 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.96, y: 12 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-line">
              <h3 className="font-semibold text-fg">{title}</h3>
              <button onClick={onClose} className="text-fg-faint hover:text-fg text-lg leading-none">✕</button>
            </div>
            <div className="p-5">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ---------------------------------------------------------------- Tabs */
export function Tabs({ tabs, active, onChange }: { tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div className="flex gap-1 p-1 rounded-xl bg-panel-2/70 border border-line-soft w-fit">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`px-3.5 py-1.5 text-xs rounded-lg transition-colors ${active === t.id ? "bg-panel text-accent font-medium" : "text-fg-dim hover:text-fg"}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- DataTable */
export function DataTable<T extends { id: string }>({
  columns,
  rows,
  rowKey,
  empty,
}: {
  columns: { key: string; label: string; render?: (row: T) => ReactNode; className?: string }[];
  rows: T[];
  rowKey: (row: T) => string;
  empty?: string;
}) {
  if (rows.length === 0) return <EmptyState title={empty ?? "No rows yet"} />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-wider text-fg-faint">
            {columns.map((c) => (
              <th key={c.key} className={`px-3 py-2.5 font-medium ${c.className ?? ""}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b border-line-soft hover:bg-panel-2/40 transition-colors">
              {columns.map((c) => (
                <td key={c.key} className={`px-3 py-2.5 align-middle ${c.className ?? ""}`}>
                  {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------------------------------------------------------------- Misc */
export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="px-1.5 py-0.5 rounded border border-line bg-panel-2 text-[10px] text-fg-dim font-mono">{children}</kbd>;
}

export function useAutoRefresh(fn: () => void, ms: number, deps: unknown[] = []) {
  const cb = useRef(fn);
  cb.current = fn;
  useEffect(() => {
    fn();
    const id = setInterval(() => cb.current(), ms);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);
}

export { MODE_COLORS };