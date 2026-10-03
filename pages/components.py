import streamlit as st
import textwrap

def render_sidebar_menu():
    css = """
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }

        .main .block-container { 
            max-width: calc(100% - 70px) !important; 
            margin-left: 70px !important;
            padding-top: 1.5rem; 
            padding-bottom: 2rem; 
            padding-right: 2rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .glass-sidebar {
            position: fixed;
            top: 0;
            left: 0;
            height: 100vh;
            width: 70px;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            flex-direction: column;
            padding-top: 25px;
            transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 999999;
            overflow: hidden;
            box-shadow: 4px 0 15px rgba(0,0,0,0.15);
            font-family: 'Inter', sans-serif;
        }

        .glass-sidebar:hover {
            width: 250px;
            background: rgba(15, 23, 42, 0.99);
        }

        .glass-logo {
            padding: 0 24px 30px;
            display: flex;
            align-items: center;
            color: white;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 15px;
            white-space: nowrap;
        }

        .glass-item {
            display: flex;
            align-items: center;
            padding: 16px 24px;
            color: rgba(255, 255, 255, 0.45);
            text-decoration: none !important;
            white-space: nowrap;
            transition: all 0.2s ease;
            border-left: 3px solid transparent;
        }

        .glass-item:hover {
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
        }

        .glass-item.active {
            background: rgba(59, 130, 246, 0.15); 
            color: #ffffff;
            border-left: 3px solid #3b82f6;
        }

        .glass-icon {
            min-width: 20px;
            font-size: 18px !important;
            margin-right: 18px;
        }

        .glass-text {
            opacity: 0;
            font-weight: 500;
            font-size: 13px;
            transition: opacity 0.2s ease;
            letter-spacing: 0.3px;
        }

        .glass-sidebar:hover .glass-text {
            opacity: 1;
            transition-delay: 0.1s;
        }
    </style>

    <div class="glass-sidebar">
        <div class="glass-logo">
            <i class="bi bi-hexagon-fill glass-icon" style="color: #3b82f6;"></i>
            <span class="glass-text" style="font-size: 15px; font-weight: 800; letter-spacing: 1px;">COCKPIT</span>
        </div>
        
        <a href="/" class="glass-item" target="_self">
            <i class="bi bi-grid-1x2 glass-icon"></i>
            <span class="glass-text">Portal Executivo</span>
        </a>
        
        <a href="Dashboard_Saldo" class="glass-item {active_saldo}" target="_self">
            <i class="bi bi-bank glass-icon"></i>
            <span class="glass-text">Dashboard Saldo</span>
        </a>
        
        <a href="painel_fluxo_caixa" class="glass-item {active_fluxo}" target="_self">
            <i class="bi bi-cash-stack glass-icon"></i>
            <span class="glass-text">Fluxo de Caixa</span>
        </a>
        
        <a href="painel_pagar" class="glass-item {active_pagar}" target="_self">
            <i class="bi bi-graph-down-arrow glass-icon"></i>
            <span class="glass-text">Painel a Pagar</span>
        </a>
    </div>
    """
    return css

