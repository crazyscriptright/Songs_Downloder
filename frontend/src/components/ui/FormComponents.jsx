export const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  disabled = false, 
  onClick, 
  className = '',
  ...props 
}) => {
  const baseStyles = 'font-medium rounded-lg transition-all-smooth focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2';
  
  const variants = {
    primary: 'text-white focus:ring-2',
    secondary: 'bg-gray-700 hover:bg-gray-600 text-white',
    accent: 'text-white',
    outline: 'border-2 hover:text-white',
    ghost: 'hover:bg-opacity-10',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
  };
  
  const getButtonStyle = (variant) => {
    const baseClasses = `${baseStyles} ${variants[variant]}`;
    if (variant === 'primary') {
      return `${baseClasses}`;
    }
    if (variant === 'accent') {
      return `${baseClasses}`;
    }
    if (variant === 'outline') {
      return `${baseClasses}`;
    }
    if (variant === 'ghost') {
      return `${baseClasses}`;
    }
    return baseClasses;
  };
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={`${getButtonStyle(variant)} ${sizes[size]} ${className}`}
      disabled={disabled}
      onClick={onClick}
      style={{
        background: variant === 'primary' ? 'var(--gradient-secondary)' :
                   variant === 'accent' ? 'var(--gradient-primary)' : undefined,
        borderColor: variant === 'outline' ? 'var(--accent-color)' : undefined,
        color: variant === 'outline' ? 'var(--accent-color)' :
               variant === 'ghost' ? 'var(--accent-color)' : undefined,
      }}
      {...props}
    >
      {children}
    </button>
  );
};

export const Input = ({ 
  label, 
  error, 
  className = '', 
  containerClassName = '',
  ...props 
}) => {
  return (
    <div className={`flex flex-col gap-1.5 ${containerClassName}`}>
      {label && (
        <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
          {label}
        </label>
      )}
      <input
        className={`
          w-full px-4 py-2 rounded-lg border
          transition-all-smooth
          focus:outline-none focus:ring-2 focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed
          ${error ? 'border-red-500' : ''}
          ${className}
        `}
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: error ? 'var(--error-color)' : 'var(--border-color)',
          color: 'var(--text-primary)',
        }}
        {...props}
      />
      {error && <span className="text-sm" style={{ color: 'var(--error-color)' }}>{error}</span>}
    </div>
  );
};

export const Select = ({ 
  label, 
  options = [], 
  className = '', 
  containerClassName = '',
  ...props 
}) => {
  return (
    <div className={`flex flex-col gap-1.5 ${containerClassName}`}>
      {label && (
        <label className="text-sm font-medium text-gray-300 dark:text-gray-300">
          {label}
        </label>
      )}
      <select
        className={`
          w-full px-4 py-2 rounded-lg border
          transition-all-smooth
          focus:outline-none focus:ring-2 focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}
        `}
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-color)',
          color: 'var(--text-primary)',
        }}
         

      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export const Checkbox = ({ label, className = '', ...props }) => {
  return (
    <label className={`flex items-center gap-2 cursor-pointer ${className}`}>
      <input
        type="checkbox"
        className="w-4 h-4 rounded focus:ring-2"
        style={{
          accentColor: 'var(--accent-color)',
        }}
        {...props}
      />
      <span className="text-sm text-gray-300">{label}</span>
    </label>
  );
};

export const TextArea = ({ 
  label, 
  error, 
  className = '', 
  containerClassName = '',
  ...props 
}) => {
  return (
    <div className={`flex flex-col gap-1.5 ${containerClassName}`}>
      {label && (
        <label className="text-sm font-medium text-gray-300 dark:text-gray-300">
          {label}
        </label>
      )}
      <textarea
        className={`
          w-full px-4 py-2 rounded-lg border resize-none
          transition-all-smooth
          focus:outline-none focus:ring-2 focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed
          ${error ? 'border-red-500' : ''}
          ${className}
        `}
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: error ? 'var(--error-color)' : 'var(--border-color)',
          color: 'var(--text-primary)',
        }}

        {...props}
      />
      {error && <span className="text-sm text-red-500">{error}</span>}
    </div>
  );
};

export const Card = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`
        rounded-xl p-6 border
        shadow-lg hover:shadow-xl transition-all-smooth
        ${className}
      `}
      style={{
        backgroundColor: 'var(--bg-card)',
        borderColor: 'var(--border-color)',
      }}
      {...props}
    >
      {children}
    </div>
  );
};

export const Badge = ({ children, variant = 'default', className = '' }) => {
  const getStyle = () => {
    switch(variant) {
      case 'primary':
        return { backgroundColor: 'var(--accent-color)', color: 'white' };
      case 'success':
        return { backgroundColor: 'var(--success-color)', color: 'white' };
      case 'error':
        return { backgroundColor: 'var(--error-color)', color: 'white' };
      case 'warning':
        return { backgroundColor: 'var(--warning-color)', color: 'white' };
      case 'info':
        return { backgroundColor: 'var(--info-color)', color: 'white' };
      default:
        return { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' };
    }
  };

  return (
    <span 
      className={`px-2 py-1 text-xs font-medium rounded-full ${className}`}
      style={getStyle()}
    >
      {children}
    </span>
  );
};

export const Spinner = ({ size = 'md', className = '' }) => {
  const sizes = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
  };

  return (
    <div
      className={`
        ${sizes[size]}
        border-gray-600 border-t-primary
        rounded-full animate-spin
        ${className}
      `}
    />
  );
};
