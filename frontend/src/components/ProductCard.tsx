"use client";

import React from "react";
import { Product } from "@/types";
import { Star, PackageCheck, Zap, Plus, Check } from "lucide-react";
import { motion } from "framer-motion";

interface ProductCardProps {
  product: Product;
  isHighlighted: boolean;
  isInCart: boolean;
  onAddToCart: (product: Product) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  isHighlighted,
  isInCart,
  onAddToCart,
}) => {
  const savings = round(product.price_inr - product.discount_price);

  function round(val: number) {
    return Math.round(val * 100) / 100;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`glass-card rounded-2xl p-4 flex flex-col justify-between transition-all duration-300 relative overflow-hidden group ${
        isHighlighted
          ? "border-2 border-orange-500 shadow-xl shadow-orange-500/20 ring-4 ring-orange-500/20 scale-[1.02]"
          : "hover:border-gray-700 hover:shadow-lg hover:shadow-black/40"
      }`}
    >
      {/* Top Badges */}
      <div className="flex items-center justify-between mb-3">
        <span className="bg-orange-500/20 text-orange-400 text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full border border-orange-500/30 flex items-center space-x-1">
          <Zap className="w-3 h-3" />
          <span>{product.category}</span>
        </span>
        <span className="text-[11px] font-bold text-gray-400 flex items-center space-x-1">
          <PackageCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>{product.stock_count} units left</span>
        </span>
      </div>

      {/* Product Image */}
      <div className="relative w-full h-44 mb-4 rounded-xl overflow-hidden bg-gray-900/60 flex items-center justify-center p-2 group-hover:scale-105 transition-transform duration-500">
        <img
          src={product.image_url}
          alt={product.name}
          className="w-full h-full object-cover rounded-lg"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-transparent to-transparent opacity-60" />
      </div>

      {/* Details */}
      <div>
        <div className="flex items-center space-x-1 mb-1">
          <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
          <span className="text-xs font-bold text-amber-400">{product.rating}</span>
          <span className="text-gray-500 text-xs font-medium">({product.flavour})</span>
        </div>

        <h3 className="font-extrabold text-sm lg:text-base text-white leading-snug line-clamp-2 mb-2 group-hover:text-orange-400 transition-colors">
          {product.name}
        </h3>

        <p className="text-xs text-gray-400 line-clamp-2 mb-4">
          {product.description}
        </p>
      </div>

      {/* Pricing & Actions */}
      <div className="pt-3 border-t border-gray-800 flex items-center justify-between mt-auto">
        <div>
          <div className="flex items-baseline space-x-2">
            <span className="text-lg lg:text-xl font-extrabold text-white">
              ₹{product.discount_price.toLocaleString("en-IN")}
            </span>
            <span className="text-xs text-gray-500 line-through">
              ₹{product.price_inr.toLocaleString("en-IN")}
            </span>
          </div>
          <span className="text-[10px] font-bold text-emerald-400 block">
            Save ₹{savings.toLocaleString("en-IN")} with FIT10
          </span>
        </div>

        <button
          onClick={() => onAddToCart(product)}
          className={`p-2.5 rounded-xl font-bold transition-all cursor-pointer flex items-center space-x-1.5 ${
            isInCart
              ? "bg-emerald-500 text-black shadow-md shadow-emerald-500/30"
              : "bg-orange-500 hover:bg-orange-600 text-black shadow-md shadow-orange-500/30"
          }`}
        >
          {isInCart ? (
            <>
              <Check className="w-4 h-4" />
              <span className="text-xs">In Stack</span>
            </>
          ) : (
            <>
              <Plus className="w-4 h-4" />
              <span className="text-xs">Add</span>
            </>
          )}
        </button>
      </div>

    </motion.div>
  );
};
