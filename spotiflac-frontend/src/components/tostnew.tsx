import React, { createContext, useContext } from "react";
import { IoCheckmarkCircle, IoClose, IoCloseCircle } from "react-icons/io5";
import { toast } from "sonner";

type ToastOptions = {
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  style?: React.CSSProperties;
};

type ToastContextType = {
  success: (msg: string, options?: ToastOptions) => void;
  error: (msg: string, options?: ToastOptions) => void;
};

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const CrossIcon = <IoClose size={16} />;
const SuccessIcon = <IoCheckmarkCircle size={20} />;
const ErrorIcon = <IoCloseCircle size={20} />;

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const renderCustomToast = (
    msg: string,
    opts?: ToastOptions,
    intent: "success" | "error" = "success",
  ) => {
    // second arg: options for sonner (duration)
    const sonnerOpts = { duration: opts?.duration ?? 2000 };

    toast.custom((t) => {
      return (
        <div
          // use Tailwind classes or inline styles — this example uses Tailwind-friendly classes
          className={`flex items-center gap-3 rounded-md p-3 shadow-lg text-sm ${
            intent === "success"
              ? "bg-green-600 text-white"
              : "bg-red-600 text-white"
          }`}
          style={opts?.style}
        >
          <div className="flex-shrink-0">
            {intent === "success" ? SuccessIcon : ErrorIcon}
          </div>
          <div className="flex-1 pr-2">{msg}</div>

          {/* optional action button passed by caller */}
          {opts?.action ? (
            <button
              onClick={() => {
                try {
                  opts.action?.onClick();
                } catch (e) {
                  /* swallow errors from caller action */
                  console.error(e);
                }
              }}
              className="bg-transparent border-none p-0 mr-1 text-white hover:opacity-80"
              aria-label={opts.action.label}
              type="button"
              style={{ background: "transparent" }}
            >
              {/* if label is short text, use it, otherwise still clickable */}
              <span className="text-sm">{opts.action.label}</span>
            </button>
          ) : null}

          {/* close button with transparent bg so no black box */}
          <button
            onClick={() => toast.dismiss(t)}
            className="bg-transparent border-none p-1 rounded hover:bg-white/10"
            aria-label="Close"
            type="button"
            style={{ background: "transparent" }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                color: "inherit",
              }}
            >
              {CrossIcon}
            </span>
          </button>
        </div>
      );
    }, sonnerOpts);
  };

  const value: ToastContextType = {
    success: (msg, options) => renderCustomToast(msg, options, "success"),
    error: (msg, options) => renderCustomToast(msg, options, "error"),
  };

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within a ToastProvider");
  return context;
};
