"use client";

import React from "react";
import { WalletInfo } from "@/types";
import { Wallet, ShieldCheck, ShoppingBag, Globe, Dumbbell } from "lucide-react";

interface HeaderProps {
  wallet: WalletInfo | null;
  selectedLang: string;
  onSelectLang: (lang: string) => void;
  cartCount: number;
  onOpenCart: () => void;
  onOpenWallet: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  wallet,
  selectedLang,
  onSelectLang,
  cartCount,
  onOpenCart,
  onOpenWallet,
}) => {
  return (
    <header className="sticky top-0 z-40 glass-card border-b border-gray-800 px-4 lg:px-8 py-3 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-orange-500/30">
            <Dumbbell className="w-6 h-6 text-black stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-white via-gray-200 to-orange-400 bg-clip-text text-transparent">
                MUSCLEBLAZE
              </span>
              <span className="bg-orange-500/20 text-orange-400 text-xs font-bold px-2 py-0.5 rounded-full border border-orange-500/30">
                VOICE AI
              </span>
            </div>
            <p className="text-[10px] text-gray-400 font-medium">Agentic Commerce Engine</p>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center space-x-3 lg:space-x-4">
          
          {/* Language Selector */}
          <div className="flex items-center space-x-1 glass-pill px-2.5 py-1.5 rounded-lg text-xs font-medium border border-gray-700">
            <Globe className="w-3.5 h-3.5 text-orange-400" />
            <select
              value={selectedLang}
              onChange={(e) => onSelectLang(e.target.value)}
              className="bg-transparent text-gray-200 focus:outline-none cursor-pointer font-semibold"
            >
              <option value="hi-IN" className="bg-gray-900 text-white">🇮🇳 Hindi (हिन्दी)</option>
              <option value="te-IN" className="bg-gray-900 text-white">🇮🇳 Telugu (తెలుగు)</option>
              <option value="en-IN" className="bg-gray-900 text-white">🇬🇧 English (IN)</option>
            </select>
          </div>

          {/* Programmable Wallet Badge */}
          <button
            onClick={onOpenWallet}
            className="flex items-center space-x-2 glass-pill hover:bg-orange-500/10 px-3 py-1.5 rounded-lg border border-orange-500/30 transition-all cursor-pointer group"
          >
            <div className="w-6 h-6 rounded-md bg-orange-500/20 flex items-center justify-center text-orange-400 group-hover:scale-105 transition-transform">
              <Wallet className="w-3.5 h-3.5" />
            </div>
            <div className="text-left">
              <div className="text-[10px] text-gray-400 leading-none flex items-center space-x-1">
                <span>WALLET</span>
                <ShieldCheck className="w-2.5 h-2.5 text-emerald-400 inline" />
              </div>
              <span className="text-xs font-extrabold text-orange-400">
                ₹{wallet ? wallet.balance.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : "0.00"}
              </span>
            </div>
          </button>

          {/* Cart Button */}
          <button
            onClick={onOpenCart}
            className="relative glass-pill hover:bg-gray-800 p-2.5 rounded-lg border border-gray-700 text-gray-200 hover:text-white transition-all cursor-pointer"
          >
            <ShoppingBag className="w-5 h-5 text-gray-300" />
            {cartCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-orange-500 text-black text-[11px] font-extrabold w-5 h-5 rounded-full flex items-center justify-center shadow-md animate-bounce">
                {cartCount}
              </span>
            )}
          </button>

        </div>
      </div>
    </header>
  );
};
