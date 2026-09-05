"use client";

import React from "react";
import { Product, CartQuote, OrderResult, WalletInfo } from "@/types";
import { X, ShoppingCart, Tag, Gift, Wallet, ExternalLink, ShieldCheck, CheckCircle2, ArrowRight } from "lucide-react";
import confetti from "canvas-confetti";

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  cart: Product[];
  onRemoveFromCart: (productId: number) => void;
  quote: CartQuote | null;
  orderResult: OrderResult | null;
  wallet: WalletInfo | null;
  onCheckoutWallet: () => void;
  onCheckoutRazorpay: () => void;
  isProcessing: boolean;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  isOpen,
  onClose,
  cart,
  onRemoveFromCart,
  quote,
  orderResult,
  wallet,
  onCheckoutWallet,
  onCheckoutRazorpay,
  isProcessing,
}) => {
  if (!isOpen) return null;

  const handleWalletPay = () => {
    onCheckoutWallet();
    confetti({ particleCount: 80, spread: 60, origin: { y: 0.6 } });
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md bg-gray-950 border-l border-gray-800 h-full flex flex-col justify-between shadow-2xl p-6 overflow-y-auto">
        
        {/* Header */}
        <div>
          <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-6">
            <div className="flex items-center space-x-2">
              <ShoppingCart className="w-5 h-5 text-orange-400" />
              <h2 className="font-extrabold text-lg text-white">Your Supplement Stack</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Cart Line Items */}
          {cart.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-30 text-gray-400" />
              <p className="text-sm font-medium">Your stack is empty.</p>
              <p className="text-xs text-gray-600 mt-1">Speak into the mic to add products!</p>
            </div>
          ) : (
            <div className="space-y-3 mb-6">
              {cart.map((item) => (
                <div key={item.id} className="glass-card p-3 rounded-xl flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <img src={item.image_url} alt={item.name} className="w-12 h-12 object-cover rounded-lg" />
                    <div>
                      <h4 className="font-bold text-xs text-white line-clamp-1">{item.name}</h4>
                      <p className="text-[11px] text-gray-400">1 x ₹{item.price_inr.toLocaleString("en-IN")}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => onRemoveFromCart(item.id)}
                    className="text-xs text-red-400 hover:text-red-300 font-medium cursor-pointer p-1"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Order Summary & Pricing Breakdown */}
          {quote && quote.items.length > 0 && (
            <div className="glass-card p-4 rounded-2xl mb-6 space-y-2.5 border border-gray-800">
              <div className="flex justify-between text-xs text-gray-300">
                <span>Subtotal ({quote.items.length} items)</span>
                <span className="font-bold text-white">₹{quote.subtotal.toLocaleString("en-IN")}</span>
              </div>

              {quote.combo_discount > 0 && (
                <div className="flex justify-between text-xs text-emerald-400 font-semibold">
                  <span className="flex items-center space-x-1">
                    <Tag className="w-3.5 h-3.5" />
                    <span>Combo Savings</span>
                  </span>
                  <span>-₹{quote.combo_discount.toLocaleString("en-IN")}</span>
                </div>
              )}

              {quote.coupon_discount > 0 && (
                <div className="flex justify-between text-xs text-orange-400 font-semibold">
                  <span className="flex items-center space-x-1">
                    <Tag className="w-3.5 h-3.5" />
                    <span>Coupon ({quote.coupon_code || 'FIT10'})</span>
                  </span>
                  <span>-₹{quote.coupon_discount.toLocaleString("en-IN")}</span>
                </div>
              )}

              {quote.free_gifts.length > 0 && (
                <div className="pt-2 border-t border-gray-800/60 flex items-center space-x-1.5 text-xs text-amber-400 font-medium">
                  <Gift className="w-3.5 h-3.5" />
                  <span>Free Gift: {quote.free_gifts.join(", ")}</span>
                </div>
              )}

              <div className="pt-3 border-t border-gray-800 flex justify-between items-baseline">
                <span className="font-extrabold text-sm text-white">Grand Total</span>
                <span className="font-extrabold text-xl text-orange-400">
                  ₹{quote.final_total.toLocaleString("en-IN")}
                </span>
              </div>
            </div>
          )}

          {/* Confirmed Order State Banner */}
          {orderResult && (
            <div className="glass-card p-4 rounded-2xl mb-6 border border-emerald-500/30 bg-emerald-950/20">
              <div className="flex items-center space-x-2 text-emerald-400 mb-2">
                <CheckCircle2 className="w-5 h-5" />
                <span className="font-extrabold text-sm uppercase tracking-wide">
                  Order Status: {orderResult.order_status}
                </span>
              </div>
              <p className="text-xs text-gray-300 mb-2">
                Order ID: <span className="font-mono text-white">{orderResult.order_id}</span>
              </p>
              
              {orderResult.wallet_paid && (
                <div className="text-xs text-gray-300 flex justify-between mb-1">
                  <span>Wallet Paid:</span>
                  <span className="font-bold text-emerald-400">{orderResult.wallet_paid}</span>
                </div>
              )}

              {orderResult.razorpay_payment_link && (
                <div className="mt-3 pt-3 border-t border-emerald-900/50">
                  <span className="text-xs text-orange-400 font-semibold block mb-1">Remaining Balance Link:</span>
                  <a
                    href={orderResult.razorpay_payment_link}
                    target="_blank"
                    rel="noreferrer"
                    className="glass-pill bg-orange-500 hover:bg-orange-600 text-black font-extrabold text-xs px-3 py-2 rounded-xl flex items-center justify-between transition-all"
                  >
                    <span>Pay {orderResult.razorpay_pending} via Razorpay</span>
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Payment Actions */}
        <div className="pt-4 border-t border-gray-800 space-y-2.5">
          
          <button
            onClick={handleWalletPay}
            disabled={isProcessing || cart.length === 0}
            className="w-full bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 disabled:opacity-50 text-black font-extrabold py-3.5 rounded-xl shadow-lg shadow-orange-500/25 transition-all flex items-center justify-center space-x-2 cursor-pointer"
          >
            <Wallet className="w-4 h-4 text-black" />
            <span>Pay via Agentic Wallet (₹{wallet?.balance.toLocaleString("en-IN")})</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={onCheckoutRazorpay}
            disabled={isProcessing || cart.length === 0}
            className="w-full bg-gray-900 hover:bg-gray-800 text-white font-bold py-3 rounded-xl border border-gray-700 transition-all flex items-center justify-center space-x-2 cursor-pointer text-xs"
          >
            <ExternalLink className="w-3.5 h-3.5 text-orange-400" />
            <span>Generate Razorpay Smart UPI Link</span>
          </button>

          <div className="flex items-center justify-center space-x-1 text-[10px] text-gray-500 pt-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>KYA Verified • Bounded Spend Rails (Max ₹15,000)</span>
          </div>

        </div>

      </div>
    </div>
  );
};
