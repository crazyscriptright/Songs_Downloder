var MyClass = React.createClass({
  render: function () {
    return (
      <div>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Bulk &amp; Playlist Downloader</title>
        <link rel="icon" type="image/png" href="static/fevicon2.png" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <style
          dangerouslySetInnerHTML={{
            __html:
              '\n      :root {\n        --bg-primary: #0f0f0f;\n        --bg-secondary: #1a1a1a;\n        --bg-card: #1f1f1f;\n        --text-primary: #f0f0f0;\n        --text-secondary: #d1d5db;\n        --text-tertiary: #9ca3af;\n        --accent-color: #34d399;\n        --accent-secondary: #10b981;\n        --border-color: #374151;\n        --shadow-color: rgba(52, 211, 153, 0.2);\n        --success-color: #34d399;\n        --error-color: #f87171;\n        --warning-color: #fbbf24;\n        --info-color: #a78bfa;\n        --gradient-primary: linear-gradient(135deg, #c084fc 0%, #7c3aed 100%);\n        --gradient-secondary: linear-gradient(135deg, #34d399 0%, #10b981 100%);\n      }\n\n      body.light-theme {\n        --bg-primary: #fafafa;\n        --bg-secondary: #f5f5f5;\n        --bg-card: #ffffff;\n        --text-primary: #2d2d2d;\n        --text-secondary: #6b7280;\n        --text-tertiary: #9ca3af;\n        --accent-color: #10b981;\n        --accent-secondary: #059669;\n        --border-color: #e5e7eb;\n        --shadow-color: rgba(16, 185, 129, 0.15);\n        --success-color: #10b981;\n        --error-color: #ef4444;\n        --warning-color: #f59e0b;\n        --info-color: #8b5cf6;\n      }\n\n      * {\n        margin: 0;\n        padding: 0;\n        box-sizing: border-box;\n      }\n\n      body {\n        font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",\n          system-ui, sans-serif;\n        background: var(--bg-primary);\n        color: var(--text-primary);\n        min-height: 100vh;\n        padding: 20px;\n        transition: all 0.3s ease;\n      }\n\n      .container {\n        max-width: 1400px;\n        margin: 0 auto;\n      }\n\n      .header {\n        text-align: center;\n        padding: 30px 0;\n        margin-bottom: 30px;\n        position: relative;\n      }\n\n      .header h1 {\n        font-size: 2.5em;\n        color: var(--accent-color);\n        font-weight: 700;\n        margin-bottom: 10px;\n      }\n\n      .header p {\n        color: var(--text-secondary);\n        font-size: 1.1em;\n      }\n\n      .nav-links {\n        position: absolute;\n        top: 30px;\n        left: 20px;\n        display: flex;\n        gap: 15px;\n      }\n\n      .nav-link {\n        background: var(--bg-card);\n        color: var(--text-secondary);\n        text-decoration: none;\n        padding: 8px 20px;\n        border-radius: 8px;\n        border: 2px solid var(--border-color);\n        transition: all 0.3s;\n        font-weight: 500;\n      }\n\n      .nav-link:hover {\n        background: var(--accent-color);\n        color: var(--bg-primary);\n        border-color: var(--accent-color);\n      }\n\n      .theme-toggle {\n        position: absolute;\n        top: 30px;\n        right: 20px;\n        background: var(--bg-card);\n        border: 2px solid var(--border-color);\n        border-radius: 25px;\n        padding: 8px 15px;\n        cursor: pointer;\n        transition: all 0.3s;\n        color: var(--text-secondary);\n      }\n\n      .theme-toggle:hover {\n        background: var(--accent-color);\n        color: var(--bg-primary);\n        border-color: var(--accent-color);\n      }\n\n      .tabs {\n        display: flex;\n        gap: 10px;\n        margin-bottom: 30px;\n        justify-content: center;\n      }\n\n      .tab-btn {\n        padding: 12px 30px;\n        font-size: 1em;\n        font-weight: 600;\n        background: var(--bg-card);\n        color: var(--text-secondary);\n        border: 2px solid var(--border-color);\n        border-radius: 10px;\n        cursor: pointer;\n        transition: all 0.3s;\n      }\n\n      .tab-btn:hover {\n        background: var(--accent-color);\n        color: var(--bg-primary);\n      }\n\n      .tab-btn.active {\n        background: var(--gradient-secondary);\n        color: white;\n        border-color: var(--accent-color);\n      }\n\n      .tab-content {\n        display: none;\n      }\n\n      .tab-content.active {\n        display: block;\n      }\n\n      .content-box {\n        background: var(--bg-card);\n        border-radius: 20px;\n        padding: 40px;\n        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);\n        border: 1px solid var(--border-color);\n        margin-bottom: 30px;\n      }\n\n      .section-title {\n        font-size: 1.5em;\n        font-weight: 700;\n        color: var(--text-primary);\n        margin-bottom: 20px;\n      }\n\n      .url-input-area {\n        width: 100%;\n        min-height: 300px;\n        padding: 15px;\n        background: var(--bg-primary);\n        border: 2px solid var(--border-color);\n        border-radius: 10px;\n        color: var(--text-primary);\n        font-family: "Courier New", monospace;\n        font-size: 0.95em;\n        resize: vertical;\n        margin-bottom: 15px;\n      }\n\n      .url-input-area:focus {\n        outline: none;\n        border-color: var(--accent-color);\n        box-shadow: 0 0 0 3px var(--shadow-color);\n      }\n\n      .input-group {\n        margin-bottom: 20px;\n      }\n\n      .input-group label {\n        display: block;\n        margin-bottom: 8px;\n        color: var(--text-secondary);\n        font-weight: 600;\n      }\n\n      .input-group input,\n      .input-group select {\n        width: 100%;\n        padding: 12px 15px;\n        background: var(--bg-primary);\n        border: 2px solid var(--border-color);\n        border-radius: 8px;\n        color: var(--text-primary);\n        font-size: 1em;\n      }\n\n      .input-group input:focus,\n      .input-group select:focus {\n        outline: none;\n        border-color: var(--accent-color);\n        box-shadow: 0 0 0 3px var(--shadow-color);\n      }\n\n      .checkbox-group {\n        display: flex;\n        align-items: center;\n        gap: 10px;\n        margin-bottom: 15px;\n      }\n\n      .checkbox-group input[type="checkbox"] {\n        width: 20px;\n        height: 20px;\n        cursor: pointer;\n      }\n\n      .checkbox-group label {\n        margin: 0;\n        color: var(--text-secondary);\n        font-weight: 500;\n        cursor: pointer;\n      }\n\n      .button-group {\n        display: flex;\n        gap: 15px;\n        margin-top: 20px;\n      }\n\n      .btn {\n        padding: 15px 40px;\n        font-size: 1.1em;\n        font-weight: 600;\n        border: none;\n        border-radius: 10px;\n        cursor: pointer;\n        transition: all 0.3s;\n        flex: 1;\n      }\n\n      .btn-primary {\n        background: var(--gradient-secondary);\n        color: white;\n      }\n\n      .btn-primary:hover {\n        transform: translateY(-2px);\n        box-shadow: 0 8px 20px var(--shadow-color);\n      }\n\n      .btn-secondary {\n        background: var(--bg-secondary);\n        color: var(--text-secondary);\n        border: 2px solid var(--border-color);\n      }\n\n      .btn-secondary:hover {\n        background: var(--border-color);\n      }\n\n      .btn:disabled {\n        opacity: 0.5;\n        cursor: not-allowed;\n        transform: none;\n      }\n\n      .progress-section {\n        margin-top: 30px;\n      }\n\n      .download-item {\n        background: var(--bg-secondary);\n        border: 1px solid var(--border-color);\n        border-radius: 10px;\n        padding: 15px;\n        margin-bottom: 10px;\n      }\n\n      .download-item.downloading {\n        border-left: 4px solid var(--info-color);\n      }\n\n      .download-item.complete {\n        border-left: 4px solid var(--success-color);\n      }\n\n      .download-item.error {\n        border-left: 4px solid var(--error-color);\n      }\n\n      .download-header {\n        display: flex;\n        justify-content: space-between;\n        align-items: center;\n        margin-bottom: 10px;\n      }\n\n      .download-title {\n        font-weight: 600;\n        color: var(--text-primary);\n      }\n\n      .download-status {\n        font-size: 0.9em;\n        padding: 4px 12px;\n        border-radius: 5px;\n        font-weight: 600;\n      }\n\n      .status-queued {\n        background: rgba(167, 139, 250, 0.2);\n        color: var(--info-color);\n      }\n\n      .status-downloading {\n        background: rgba(52, 211, 153, 0.2);\n        color: var(--accent-color);\n      }\n\n      .status-complete {\n        background: rgba(52, 211, 153, 0.2);\n        color: var(--success-color);\n      }\n\n      .status-error {\n        background: rgba(248, 113, 113, 0.2);\n        color: var(--error-color);\n      }\n\n      .progress-bar {\n        width: 100%;\n        height: 8px;\n        background: var(--border-color);\n        border-radius: 4px;\n        overflow: hidden;\n        margin-bottom: 8px;\n      }\n\n      .progress-fill {\n        height: 100%;\n        background: var(--accent-color);\n        transition: width 0.3s;\n        border-radius: 4px;\n      }\n\n      .download-info {\n        font-size: 0.85em;\n        color: var(--text-tertiary);\n      }\n\n      .download-link {\n        display: inline-block;\n        margin-top: 8px;\n        padding: 8px 16px;\n        background: var(--accent-color);\n        color: white;\n        text-decoration: none;\n        border-radius: 6px;\n        font-size: 0.9em;\n        font-weight: 600;\n        transition: all 0.3s;\n      }\n\n      .download-link:hover {\n        background: var(--accent-secondary);\n        transform: translateY(-2px);\n        box-shadow: 0 4px 12px var(--shadow-color);\n      }\n\n      .download-link svg {\n        vertical-align: middle;\n        margin-right: 5px;\n      }\n\n      /* Download Manager Styles */\n      .download-manager {\n        position: fixed;\n        top: 20px;\n        right: 20px;\n        width: 400px;\n        max-height: 70vh;\n        background: var(--bg-card);\n        border: 1px solid var(--border-color);\n        border-radius: 12px;\n        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);\n        z-index: 1000;\n        overflow: hidden;\n        display: none;\n      }\n\n      .download-manager.show {\n        display: flex;\n        flex-direction: column;\n      }\n\n      .download-manager-header {\n        padding: 15px 20px;\n        background: var(--accent-color);\n        color: white;\n        display: flex;\n        justify-content: space-between;\n        align-items: center;\n        border-radius: 12px 12px 0 0;\n      }\n\n      .download-manager-header h3 {\n        margin: 0;\n        font-size: 1.1em;\n        font-weight: 600;\n      }\n\n      .download-manager-list {\n        flex: 1;\n        overflow-y: auto;\n        padding: 10px;\n      }\n\n      .manager-download-item {\n        background: var(--bg-secondary);\n        border: 1px solid var(--border-color);\n        border-radius: 8px;\n        padding: 12px;\n        margin-bottom: 10px;\n      }\n\n      .manager-download-item.complete {\n        border-left: 4px solid var(--success-color);\n      }\n\n      .manager-download-item.downloading {\n        border-left: 4px solid var(--info-color);\n      }\n\n      .manager-download-item.error {\n        border-left: 4px solid var(--error-color);\n      }\n\n      .manager-download-title {\n        font-weight: 600;\n        font-size: 0.9em;\n        margin-bottom: 8px;\n        color: var(--text-primary);\n        overflow: hidden;\n        text-overflow: ellipsis;\n        white-space: nowrap;\n      }\n\n      .manager-progress-bar {\n        width: 100%;\n        height: 6px;\n        background: var(--border-color);\n        border-radius: 3px;\n        overflow: hidden;\n        margin-bottom: 6px;\n      }\n\n      .manager-progress-fill {\n        height: 100%;\n        background: var(--accent-color);\n        transition: width 0.3s;\n      }\n\n      .manager-download-info {\n        font-size: 0.8em;\n        color: var(--text-tertiary);\n        display: flex;\n        justify-content: space-between;\n        align-items: center;\n      }\n\n      .manager-download-link {\n        display: inline-block;\n        padding: 4px 12px;\n        background: var(--accent-color);\n        color: white;\n        text-decoration: none;\n        border-radius: 4px;\n        font-size: 0.75em;\n        font-weight: 600;\n        margin-top: 6px;\n      }\n\n      .manager-download-link:hover {\n        background: var(--accent-secondary);\n      }\n\n      .download-manager-toggle {\n        position: fixed;\n        bottom: 30px;\n        right: 30px;\n        width: 60px;\n        height: 60px;\n        background: var(--accent-color);\n        color: white;\n        border: none;\n        border-radius: 50%;\n        cursor: pointer;\n        box-shadow: 0 4px 20px var(--shadow-color);\n        z-index: 999;\n        display: flex;\n        align-items: center;\n        justify-content: center;\n        font-size: 1.5em;\n        transition: all 0.3s;\n      }\n\n      .download-manager-toggle:hover {\n        transform: scale(1.1);\n        box-shadow: 0 6px 30px var(--shadow-color);\n      }\n\n      .download-manager-toggle .badge {\n        position: absolute;\n        top: -5px;\n        right: -5px;\n        background: var(--error-color);\n        color: white;\n        border-radius: 50%;\n        width: 24px;\n        height: 24px;\n        font-size: 0.6em;\n        display: flex;\n        align-items: center;\n        justify-content: center;\n        font-weight: bold;\n      }\n\n      .close-manager-btn {\n        background: rgba(255, 255, 255, 0.2);\n        border: none;\n        color: white;\n        border-radius: 5px;\n        padding: 5px 10px;\n        cursor: pointer;\n        font-size: 0.9em;\n      }\n\n      .close-manager-btn:hover {\n        background: rgba(255, 255, 255, 0.3);\n      }\n\n      .stats {\n        display: grid;\n        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));\n        gap: 15px;\n        margin-top: 20px;\n      }\n\n      .stat-card {\n        background: var(--bg-secondary);\n        border: 1px solid var(--border-color);\n        border-radius: 10px;\n        padding: 15px 10px;\n        text-align: center;\n        min-width: 0;\n      }\n\n      .stat-value {\n        font-size: 1.8em;\n        font-weight: 700;\n        color: var(--accent-color);\n        margin-bottom: 5px;\n      }\n\n      .stat-label {\n        color: var(--text-secondary);\n        font-size: 0.85em;\n        word-wrap: break-word;\n      }\n\n      .help-text {\n        font-size: 0.9em;\n        color: var(--text-tertiary);\n        margin-top: 8px;\n      }\n\n      .options-grid {\n        display: grid;\n        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));\n        gap: 20px;\n        margin-top: 20px;\n      }\n\n      @media (max-width: 768px) {\n        .header h1 {\n          font-size: 1.8em;\n        }\n\n        .nav-links {\n          position: static;\n          justify-content: center;\n          margin-bottom: 15px;\n        }\n\n        .theme-toggle {\n          position: static;\n          display: block;\n          margin: 15px auto;\n          width: fit-content;\n        }\n\n        .content-box {\n          padding: 20px;\n        }\n\n        .button-group {\n          flex-direction: column;\n        }\n\n        .options-grid {\n          grid-template-columns: 1fr;\n        }\n\n        .stats {\n          display: flex;\n          justify-content: space-between;\n          gap: 8px;\n        }\n\n        .stat-card {\n          flex: 1;\n          padding: 10px 5px;\n          min-width: 0;\n        }\n\n        .stat-value {\n          font-size: 1.4em;\n        }\n\n        .stat-label {\n          font-size: 0.7em;\n          line-height: 1.2;\n        }\n      }\n\n      @media (max-width: 480px) {\n        .stats {\n          display: flex;\n          justify-content: space-between;\n          gap: 6px;\n        }\n\n        .stat-card {\n          flex: 1;\n          padding: 8px 4px;\n          min-width: 0;\n        }\n\n        .stat-value {\n          font-size: 1.2em;\n        }\n\n        .stat-label {\n          font-size: 0.65em;\n          line-height: 1.1;\n        }\n      }\n\n      /* YouTube Direct Download Modal */\n      .yt-modal {\n        display: none;\n        position: fixed;\n        top: 0;\n        left: 0;\n        width: 100%;\n        height: 100%;\n        background: rgba(0, 0, 0, 0.8);\n        z-index: 10000;\n        align-items: center;\n        justify-content: center;\n        animation: fadeIn 0.3s ease;\n      }\n\n      .yt-modal.show {\n        display: flex;\n      }\n\n      .yt-modal-content {\n        background: var(--bg-card);\n        border-radius: 20px;\n        padding: 40px;\n        max-width: 600px;\n        width: 90%;\n        max-height: 90vh;\n        overflow-y: auto;\n        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);\n        animation: slideUp 0.3s ease;\n      }\n\n      .yt-modal-header {\n        display: flex;\n        justify-content: space-between;\n        align-items: center;\n        margin-bottom: 25px;\n      }\n\n      .yt-modal-header h2 {\n        font-size: 24px;\n        color: var(--text-primary);\n      }\n\n      .yt-modal-close {\n        background: none;\n        border: none;\n        font-size: 30px;\n        color: var(--text-secondary);\n        cursor: pointer;\n        padding: 0;\n        width: 35px;\n        height: 35px;\n        display: flex;\n        align-items: center;\n        justify-content: center;\n        border-radius: 8px;\n        transition: all 0.2s ease;\n      }\n\n      .yt-modal-close:hover {\n        background: var(--bg-secondary);\n        color: var(--text-primary);\n      }\n\n      .yt-input-group {\n        margin-bottom: 20px;\n      }\n\n      .yt-input-group label {\n        display: block;\n        color: var(--text-secondary);\n        font-weight: 600;\n        margin-bottom: 8px;\n        font-size: 14px;\n      }\n\n      .yt-input-group input[type="text"],\n      .yt-input-group input[type="number"],\n      .yt-input-group select {\n        width: 100%;\n        padding: 12px 16px;\n        border: 2px solid var(--border-color);\n        border-radius: 10px;\n        background: var(--bg-secondary);\n        color: var(--text-primary);\n        font-size: 15px;\n        transition: all 0.2s ease;\n      }\n\n      .yt-input-group input:focus,\n      .yt-input-group select:focus {\n        outline: none;\n        border-color: var(--accent-color);\n      }\n\n      .yt-btn {\n        width: 100%;\n        padding: 14px 20px;\n        border: none;\n        border-radius: 10px;\n        font-size: 16px;\n        font-weight: 600;\n        cursor: pointer;\n        transition: all 0.3s ease;\n        background: var(--gradient-primary);\n        color: white;\n      }\n\n      .yt-btn:hover:not(:disabled) {\n        transform: translateY(-2px);\n        box-shadow: 0 10px 20px var(--shadow-color);\n      }\n\n      .yt-btn:disabled {\n        opacity: 0.5;\n        cursor: not-allowed;\n      }\n\n      .yt-advanced-toggle {\n        background: var(--bg-secondary);\n        color: var(--text-primary);\n        padding: 10px;\n        margin-bottom: 15px;\n      }\n\n      .yt-advanced-options {\n        display: none;\n        margin-bottom: 20px;\n      }\n\n      .yt-advanced-options.show {\n        display: block;\n      }\n\n      .yt-option-row {\n        display: grid;\n        grid-template-columns: 1fr 1fr;\n        gap: 15px;\n      }\n\n      .yt-progress {\n        margin-top: 20px;\n        padding: 15px;\n        background: rgba(52, 211, 153, 0.1);\n        border: 2px solid rgba(52, 211, 153, 0.3);\n        border-radius: 10px;\n        text-align: center;\n        display: none;\n      }\n\n      .yt-progress.show {\n        display: block;\n      }\n\n      @keyframes fadeIn {\n        from {\n          opacity: 0;\n        }\n        to {\n          opacity: 1;\n        }\n      }\n\n      @keyframes slideUp {\n        from {\n          opacity: 0;\n          transform: translateY(30px);\n        }\n        to {\n          opacity: 1;\n          transform: translateY(0);\n        }\n      }\n\n      /* YouTube Direct Download Modal */\n      .yt-modal {\n        display: none;\n        position: fixed;\n        top: 0;\n        left: 0;\n        width: 100%;\n        height: 100%;\n        background: rgba(0, 0, 0, 0.8);\n        z-index: 10000;\n        align-items: center;\n        justify-content: center;\n        animation: fadeIn 0.3s ease;\n      }\n\n      .yt-modal.show {\n        display: flex;\n      }\n\n      .yt-modal-content {\n        background: var(--bg-card);\n        border-radius: 20px;\n        padding: 40px;\n        max-width: 600px;\n        width: 90%;\n        max-height: 90vh;\n        overflow-y: auto;\n        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);\n        animation: slideUp 0.3s ease;\n      }\n\n      .yt-modal-header {\n        display: flex;\n        justify-content: space-between;\n        align-items: center;\n        margin-bottom: 25px;\n      }\n\n      .yt-modal-header h2 {\n        font-size: 24px;\n        color: var(--text-primary);\n      }\n\n      .yt-modal-close {\n        background: none;\n        border: none;\n        font-size: 30px;\n        color: var(--text-secondary);\n        cursor: pointer;\n        padding: 0;\n        width: 35px;\n        height: 35px;\n        display: flex;\n        align-items: center;\n        justify-content: center;\n        border-radius: 8px;\n        transition: all 0.2s ease;\n      }\n\n      .yt-modal-close:hover {\n        background: var(--bg-secondary);\n        color: var(--text-primary);\n      }\n\n      .yt-input-group {\n        margin-bottom: 20px;\n      }\n\n      .yt-input-group label {\n        display: block;\n        color: var(--text-secondary);\n        font-weight: 600;\n        margin-bottom: 8px;\n        font-size: 14px;\n      }\n\n      .yt-input-group input[type="text"],\n      .yt-input-group input[type="number"],\n      .yt-input-group select {\n        width: 100%;\n        padding: 12px 16px;\n        border: 2px solid var(--border-color);\n        border-radius: 10px;\n        background: var(--bg-secondary);\n        color: var(--text-primary);\n        font-size: 15px;\n        transition: all 0.2s ease;\n      }\n\n      .yt-input-group input:focus,\n      .yt-input-group select:focus {\n        outline: none;\n        border-color: var(--accent-color);\n      }\n\n      .yt-btn {\n        width: 100%;\n        padding: 14px 20px;\n        border: none;\n        border-radius: 10px;\n        font-size: 16px;\n        font-weight: 600;\n        cursor: pointer;\n        transition: all 0.3s ease;\n        background: var(--gradient-primary);\n        color: white;\n      }\n\n      .yt-btn:hover:not(:disabled) {\n        transform: translateY(-2px);\n        box-shadow: 0 10px 20px var(--shadow-color);\n      }\n\n      .yt-btn:disabled {\n        opacity: 0.5;\n        cursor: not-allowed;\n      }\n\n      .yt-advanced-toggle {\n        background: var(--bg-secondary);\n        color: var(--text-primary);\n        padding: 10px;\n        margin-bottom: 15px;\n      }\n\n      .yt-advanced-options {\n        display: none;\n        margin-bottom: 20px;\n      }\n\n      .yt-advanced-options.show {\n        display: block;\n      }\n\n      .yt-option-row {\n        display: grid;\n        grid-template-columns: 1fr 1fr;\n        gap: 15px;\n      }\n\n      .yt-progress {\n        margin-top: 20px;\n        padding: 15px;\n        background: rgba(52, 211, 153, 0.1);\n        border: 2px solid rgba(52, 211, 153, 0.3);\n        border-radius: 10px;\n        text-align: center;\n        display: none;\n      }\n\n      .yt-progress.show {\n        display: block;\n      }\n    ',
          }}
        />
        <div className="container">
          <div className="header">
            <div className="nav-links">
              <a href="index.html" className="nav-link">
                ← Home
              </a>
            </div>
            <button className="theme-toggle" onclick="toggleTheme()">
              Theme
            </button>
            <h1>Bulk &amp; Playlist Downloader</h1>
            <p>Download multiple songs or entire playlists at once</p>
          </div>
          <div className="tabs">
            <button className="tab-btn active" onclick="switchTab('bulk')">
              Bulk URLs
            </button>
            <button className="tab-btn" onclick="switchTab('playlist')">
              Playlist
            </button>
          </div>
          {/* Bulk URLs Tab */}
          <div id="bulk-tab" className="tab-content active">
            <div className="content-box">
              <h2 className="section-title">Bulk URL Downloader</h2>
              <p className="help-text">
                Paste one URL per line. Downloads will be processed
                sequentially.
              </p>
              <textarea
                id="bulkUrls"
                className="url-input-area"
                placeholder="https://www.youtube.com/watch?v=...
https://soundcloud.com/...
https://www.jiosaavn.com/song/...

Paste your URLs here (one per line)"
                defaultValue={""}
              />
              {/* Download Type Selector for YouTube URLs */}
              <div
                className="download-type-selector"
                style={{ marginBottom: "20px" }}
              >
                <label
                  style={{
                    display: "block",
                    marginBottom: "10px",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                  }}
                >
                  Download Type (YouTube only):
                </label>
                <div style={{ display: "flex", gap: "15px" }}>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="radio"
                      name="bulkDownloadType"
                      defaultValue="music"
                      defaultChecked
                      style={{ marginRight: "8px" }}
                      onchange="toggleBulkDownloadOptions()"
                    />
                    <span>🎵 Music (Audio Only)</span>
                  </label>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="radio"
                      name="bulkDownloadType"
                      defaultValue="video"
                      style={{ marginRight: "8px" }}
                      onchange="toggleBulkDownloadOptions()"
                    />
                    <span>🎬 Video</span>
                  </label>
                </div>
              </div>
              {/* Audio Options */}
              <div id="bulkAudioOptions" className="options-section">
                <div className="options-grid">
                  <div className="input-group">
                    <label>Audio Format</label>
                    <select id="bulkAudioFormat">
                      <option value="mp3">MP3</option>
                      <option value="m4a">M4A</option>
                      <option value="opus">Opus</option>
                      <option value="vorbis">Vorbis</option>
                      <option value="wav">WAV</option>
                      <option value="flac">FLAC</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Audio Quality</label>
                    <select id="bulkAudioQuality">
                      <option value={0}>Best (0)</option>
                      <option value={2}>High (2)</option>
                      <option value={5}>Medium (5)</option>
                      <option value={9}>Low (9)</option>
                    </select>
                  </div>
                </div>
                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id="bulkEmbedThumbnail"
                    defaultChecked
                  />
                  <label htmlFor="bulkEmbedThumbnail">Embed Thumbnail</label>
                </div>
              </div>
              {/* Video Options */}
              <div
                id="bulkVideoOptions"
                className="options-section"
                style={{ display: "none" }}
              >
                <div className="options-grid">
                  <div className="input-group">
                    <label>Video Quality</label>
                    <select id="bulkVideoQuality">
                      <option value={2160}>4K (2160p)</option>
                      <option value={1440}>2K (1440p)</option>
                      <option value={1080} selected>
                        Full HD (1080p)
                      </option>
                      <option value={720}>HD (720p)</option>
                      <option value={480}>SD (480p)</option>
                      <option value={360}>Low (360p)</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Video FPS</label>
                    <select id="bulkVideoFPS">
                      <option value={60}>60 FPS</option>
                      <option value={30} selected>
                        30 FPS
                      </option>
                      <option value={24}>24 FPS</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Video Format</label>
                    <select id="bulkVideoFormat">
                      <option value="mkv" selected>
                        MKV (Best Quality)
                      </option>
                      <option value="mp4">MP4 (Compatible)</option>
                      <option value="webm">WebM</option>
                    </select>
                  </div>
                </div>
                <div className="checkbox-group">
                  <input type="checkbox" id="bulkEmbedSubs" defaultChecked />
                  <label htmlFor="bulkEmbedSubs">Embed Subtitles</label>
                </div>
              </div>
              {/* Common Options */}
              <div className="checkbox-group">
                <input type="checkbox" id="bulkAddMetadata" defaultChecked />
                <label htmlFor="bulkAddMetadata">Add Metadata</label>
              </div>
              <div className="button-group">
                <button
                  className="btn btn-primary"
                  onclick="startBulkDownload()"
                >
                  Start Bulk Download
                </button>
                <button className="btn btn-secondary" onclick="clearBulkUrls()">
                  Clear URLs
                </button>
              </div>
              <div className="stats">
                <div className="stat-card">
                  <div className="stat-value" id="totalUrls">
                    0
                  </div>
                  <div className="stat-label">Total URLs</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" id="completedDownloads">
                    0
                  </div>
                  <div className="stat-label">Completed</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" id="failedDownloads">
                    0
                  </div>
                  <div className="stat-label">Failed</div>
                </div>
              </div>
            </div>
            <div className="progress-section" id="bulkProgress" />
          </div>
          {/* Playlist Tab */}
          <div id="playlist-tab" className="tab-content">
            <div className="content-box">
              <h2 className="section-title">Playlist Downloader</h2>
              <p className="help-text">
                Download entire playlists from YouTube with advanced options
              </p>
              <div className="input-group">
                <label>Playlist URL</label>
                <input
                  type="text"
                  id="playlistUrl"
                  placeholder="https://www.youtube.com/playlist?list=..."
                />
              </div>
              <div className="options-grid">
                <div className="input-group">
                  <label>Download Type</label>
                  <select id="playlistType" onchange="togglePlaylistOptions()">
                    <option value="audio">Audio Only</option>
                    <option value="video">Video</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Playlist Items</label>
                  <select id="playlistItems">
                    <option value="all">All Items</option>
                    <option value="custom">Custom Range</option>
                  </select>
                </div>
              </div>
              <div
                className="input-group"
                id="customRangeGroup"
                style={{ display: "none" }}
              >
                <label>Custom Range (e.g., 1-5, 10, 15-20)</label>
                <input
                  type="text"
                  id="customRange"
                  placeholder="1-5,10,15-20"
                />
              </div>
              {/* Audio Options */}
              <div id="audioOptions">
                <h3
                  style={{
                    margin: "20px 0 15px",
                    color: "var(--text-secondary)",
                  }}
                >
                  Audio Options
                </h3>
                <div className="options-grid">
                  <div className="input-group">
                    <label>Audio Format</label>
                    <select id="playlistAudioFormat">
                      <option value="mp3">MP3</option>
                      <option value="m4a">M4A</option>
                      <option value="opus">Opus</option>
                      <option value="vorbis">Vorbis</option>
                      <option value="wav">WAV</option>
                      <option value="flac">FLAC</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Audio Quality</label>
                    <select id="playlistAudioQuality">
                      <option value={0}>Best (0)</option>
                      <option value={2}>High (2)</option>
                      <option value={5}>Medium (5)</option>
                      <option value={9}>Low (9)</option>
                    </select>
                  </div>
                </div>
                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id="playlistEmbedThumbnail"
                    defaultChecked
                  />
                  <label htmlFor="playlistEmbedThumbnail">
                    Embed Thumbnail
                  </label>
                </div>
                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id="playlistAddMetadata"
                    defaultChecked
                  />
                  <label htmlFor="playlistAddMetadata">Add Metadata</label>
                </div>
              </div>
              {/* Video Options */}
              <div id="videoOptions" style={{ display: "none" }}>
                <h3
                  style={{
                    margin: "20px 0 15px",
                    color: "var(--text-secondary)",
                  }}
                >
                  Video Options
                </h3>
                <div className="options-grid">
                  <div className="input-group">
                    <label>Video Quality</label>
                    <select id="playlistVideoQuality">
                      <option value="best">Best Available</option>
                      <option value={2160}>4K (2160p)</option>
                      <option value={1440}>2K (1440p)</option>
                      <option value={1080}>Full HD (1080p)</option>
                      <option value={720}>HD (720p)</option>
                      <option value={480}>SD (480p)</option>
                      <option value={360}>Low (360p)</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Frame Rate</label>
                    <select id="playlistVideoFPS">
                      <option value="any">Any FPS</option>
                      <option value={60}>60 FPS</option>
                      <option value={30}>30 FPS</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Video Format</label>
                    <select id="playlistVideoFormat">
                      <option value="mkv">MKV</option>
                      <option value="mp4">MP4</option>
                      <option value="webm">WebM</option>
                    </select>
                  </div>
                </div>
                <div className="checkbox-group">
                  <input type="checkbox" id="playlistEmbedSubtitles" />
                  <label htmlFor="playlistEmbedSubtitles">
                    Embed Subtitles
                  </label>
                </div>
              </div>
              <div className="button-group">
                <button
                  className="btn btn-primary"
                  onclick="startPlaylistDownload()"
                >
                  Download Playlist
                </button>
                <button
                  className="btn btn-secondary"
                  onclick="clearPlaylistUrl()"
                >
                  Clear URL
                </button>
              </div>
              <div className="stats">
                <div className="stat-card">
                  <div className="stat-value" id="playlistTotal">
                    0
                  </div>
                  <div className="stat-label">Total Items</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" id="playlistCompleted">
                    0
                  </div>
                  <div className="stat-label">Completed</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" id="playlistFailed">
                    0
                  </div>
                  <div className="stat-label">Failed</div>
                </div>
              </div>
            </div>
            <div className="progress-section" id="playlistProgress" />
          </div>
        </div>
        {/* Download Manager */}
        <div id="downloadManager" className="download-manager">
          <div className="download-manager-header">
            <h3>Downloads</h3>
            <button
              className="close-manager-btn"
              onclick="toggleDownloadManager()"
            >
              Close
            </button>
          </div>
          <div className="download-manager-list" id="downloadManagerList">
            <div
              style={{
                textAlign: "center",
                padding: "20px",
                color: "var(--text-tertiary)",
              }}
            >
              No active downloads
            </div>
          </div>
        </div>
        {/* Download Manager Toggle Button */}
        <button
          id="downloadManagerToggle"
          className="download-manager-toggle"
          onclick="toggleDownloadManager()"
        >
          <svg
            width={24}
            height={24}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1={12} y1={15} x2={12} y2={3} />
          </svg>
          <span
            className="badge"
            id="downloadBadge"
            style={{ display: "none" }}
          >
            0
          </span>
        </button>
      </div>
    );
  },
});
