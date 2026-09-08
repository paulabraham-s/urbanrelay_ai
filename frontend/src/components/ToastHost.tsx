import { AnimatePresence, motion } from "framer-motion";
import { useToastStore } from "../stores/toasts";

const KIND_STYLE = {
  info: { border: "#1e2a44", icon: "ℹ", color: "#38bdf8" },
  success: { border: "#34d39955", icon: "✓", color: "#34d399" },
  warning: { border: "#f59e0b55", icon: "⚠", color: "#f59e0b" },
  error: { border: "#fb718555", icon: "✕", color: "#fb7185" },
};

export function ToastHost() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);
  return (
    <div className="fixed top-16 right-5 z-[1400] flex flex-col gap-2 w-[340px] max-w-[92vw]">
      <AnimatePresence>
        {toasts.map((t) => {
          const style = KIND_STYLE[t.kind];
          return (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 40 }}
              className="glass rounded-xl px-4 py-3 flex items-start gap-3 shadow-xl"
              style={{ borderColor: style.border }}
            >
              <span className="text-sm mt-0.5" style={{ color: style.color }}>{style.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium text-fg">{t.title}</div>
                {t.body && <div className="text-[11px] text-fg-dim mt-0.5 break-words">{t.body}</div>}
              </div>
              <button onClick={() => dismiss(t.id)} className="text-fg-faint hover:text-fg text-xs">✕</button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}