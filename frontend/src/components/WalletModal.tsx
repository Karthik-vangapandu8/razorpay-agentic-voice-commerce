"use client";

import React, { useState } from "react";
import { WalletInfo } from "@/types";
import { X, Wallet, ShieldCheck, ArrowUpRight, ArrowDownLeft, Clock, PlusCircle, Loader2 } from "lucide-react";

interface WalletModalProps {
  isOpen: boolean;
  onClose: () => void;
  wallet: WalletInfo | null;
  onTopUpSuccess?: () => void;
}

const API_BASE = "http://localhost:8000";

export const WalletModal: React.FC<WalletModalProps> = ({
  isOpen,
  onClose,
  wallet,
  onTopUpSuccess,
}) => {
  const [topupAmount, setTopupAmount] = useState<string>("");
  const [isTopUpLoading, setIsTopUpLoading] = useState<boolean>(false);
  const [topupSuccessMsg, setTopupSuccessMsg] = useState<string>("");

  if (!isOpen || !wallet) return null;

  const handleTopUp = async (amountToAdd: number) => {
    if (amountToAdd <= 0) return;
    setIsTopUpLoading(true);
    setTopupSuccessMsg("");
    try {
      const res = await fetch(`${API_BASE}/api/wallet/topup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: wallet.customer_name || "Kartik",
          amount: amountToAdd
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTopupSuccessMsg(`Successfully added ₹${amountToAdd.toLocaleString("en-IN")} to wallet!`);
        setTopupAmount("");
        if (onTopUpSuccess) onTopUpSuccess();
        setTimeout(() => setTopupSuccessMsg(""), 4000);
      }
    } catch (e) {
      console.error("Top-up error:", e);
    } finally {
      setIsTopUpLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-lg glass-card bg-gray-950 border border-gray-800 rounded-3xl p-6 lg:p-8 shadow-2xl relative">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-orange-400">
              <Wallet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-lg text-white">Programmable Agentic Wallet</h3>
              <span className="text-[11px] text-gray-400 font-medium">ID: {wallet.wallet_id}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Balance Card */}
        <div className="bg-gradient-to-br from-gray-900 to-gray-950 p-6 rounded-2xl border border-gray-800 mb-6 relative overflow-hidden">
          <div className="absolute top-3 right-3 flex items-center space-x-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>KYA VERIFIED</span>
          </div>

          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-1">
            Available Balance
          </span>
          <div className="text-3xl lg:text-4xl font-black text-white tracking-tight mb-4">
            ₹{wallet.balance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>

          <div className="grid grid-cols-2 gap-3 pt-4 border-t border-gray-800/80 text-xs">
            <div>
              <span className="text-gray-500 block text-[10px]">DAILY SPEND LIMIT</span>
              <span className="font-bold text-gray-200">₹{wallet.daily_spend_limit.toLocaleString("en-IN")}</span>
            </div>
            <div>
              <span className="text-gray-500 block text-[10px]">REMAINING TODAY</span>
              <span className="font-bold text-orange-400">₹{wallet.remaining_daily_limit.toLocaleString("en-IN")}</span>
            </div>
          </div>
        </div>

        {/* Top-Up Section */}
        <div className="bg-gray-900/60 p-4 rounded-2xl border border-gray-800/80 mb-6 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-bold text-xs uppercase tracking-wider text-orange-400 flex items-center space-x-1.5">
              <PlusCircle className="w-4 h-4" />
              <span>Top-Up Wallet Funds</span>
            </h4>
            {topupSuccessMsg && (
              <span className="text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                {topupSuccessMsg}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {[500, 1000, 2000].map((amt) => (
              <button
                key={amt}
                disabled={isTopUpLoading}
                onClick={() => handleTopUp(amt)}
                className="flex-1 py-2 px-3 rounded-xl bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/30 text-orange-400 font-extrabold text-xs transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
              >
                + ₹{amt}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-2 pt-1">
            <input
              type="number"
              placeholder="Enter custom amount (e.g. 1500)"
              value={topupAmount}
              onChange={(e) => setTopupAmount(e.target.value)}
              className="flex-1 bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-orange-500"
            />
            <button
              disabled={isTopUpLoading || !topupAmount || parseFloat(topupAmount) <= 0}
              onClick={() => handleTopUp(parseFloat(topupAmount))}
              className="py-2 px-4 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-white font-extrabold text-xs shadow-lg shadow-orange-500/20 hover:opacity-90 transition-all disabled:opacity-50 flex items-center space-x-1 cursor-pointer"
            >
              {isTopUpLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <span>Add Funds</span>}
            </button>
          </div>
        </div>

        {/* Ledger Transaction History */}
        <div>
          <h4 className="font-bold text-xs uppercase tracking-wider text-gray-400 mb-3 flex items-center space-x-1">
            <Clock className="w-3.5 h-3.5 text-orange-400" />
            <span>Transaction Ledger</span>
          </h4>

          {wallet.transactions.length === 0 ? (
            <p className="text-xs text-gray-500 text-center py-4">No recent transactions.</p>
          ) : (
            <div className="space-y-2.5 max-h-40 overflow-y-auto pr-1">
              {wallet.transactions.map((tx) => (
                <div key={tx.tx_id} className="glass-card p-3 rounded-xl flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      tx.tx_type === "DEBIT_PURCHASE" ? "bg-red-500/10 text-red-400" : "bg-emerald-500/10 text-emerald-400"
                    }`}>
                      {tx.tx_type === "DEBIT_PURCHASE" ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownLeft className="w-4 h-4" />}
                    </div>
                    <div>
                      <p className="font-bold text-white leading-snug">{tx.description}</p>
                      <span className="text-[10px] text-gray-500">{tx.timestamp}</span>
                    </div>
                  </div>
                  <span className={`font-extrabold ${tx.tx_type === "DEBIT_PURCHASE" ? "text-red-400" : "text-emerald-400"}`}>
                    {tx.tx_type === "DEBIT_PURCHASE" ? "-" : "+"}₹{tx.amount.toLocaleString("en-IN")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
