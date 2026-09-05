"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { WalletInfo, Product } from "@/types";
import {
  Store,
  Package,
  Settings,
  FileText,
  Receipt,
  Plus,
  Trash2,
  Edit,
  Save,
  CheckCircle,
  AlertCircle,
  Loader2,
  DollarSign,
  Layers,
  Sparkles,
  ShieldCheck,
  ArrowUpRight
} from "lucide-react";

const API_BASE = "http://localhost:8000";

interface MerchantConfig {
  store_name: str;
  agent_name: str;
  agent_tone: str;
  active_coupon: str;
  discount_percentage: number;
  free_gift_threshold: number;
  free_gift_name: str;
  active_offers: string[];
  knowledge_specs: string;
}

export default function MerchantDashboard() {
  const [selectedLang, setSelectedLang] = useState<string>("hi-IN");
  const [wallet, setWallet] = useState<WalletInfo | null>(null);
  const [activeTab, setActiveTab] = useState<"products" | "config" | "knowledge" | "orders">("products");

  // State
  const [products, setProducts] = useState<any[]>([]);
  const [config, setConfig] = useState<MerchantConfig | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [saveStatus, setSaveStatus] = useState<string>("");

  // Product Add / Edit Modal state
  const [showProductModal, setShowProductModal] = useState<boolean>(false);
  const [editingProductId, setEditingProductId] = useState<number | null>(null);
  const [productForm, setProductForm] = useState({
    name: "",
    category: "Protein",
    flavour: "Standard",
    price_inr: 2999,
    stock_count: 50,
    rating: 4.8,
    description: "",
    image_url: ""
  });

  useEffect(() => {
    fetchWallet();
    fetchConfig();
    fetchProducts();
    fetchOrders();
  }, []);

  const fetchWallet = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/wallet?customer_name=Kartik`);
      if (res.ok) setWallet(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/merchant/config`);
      if (res.ok) setConfig(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProducts = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/merchant/products`);
      if (res.ok) {
        const data = await res.json();
        setProducts(data.products || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/merchant/orders`);
      if (res.ok) {
        const data = await res.json();
        setOrders(data.orders || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Handle Save Store Config
  const handleSaveConfig = async () => {
    if (!config) return;
    setSaveStatus("Saving...");
    try {
      const res = await fetch(`${API_BASE}/api/merchant/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config)
      });
      if (res.ok) {
        setSaveStatus("Configuration Saved!");
        setTimeout(() => setSaveStatus(""), 3000);
      }
    } catch (e) {
      setSaveStatus("Failed to save.");
    }
  };

  // Handle Add or Edit Product
  const handleSaveProduct = async () => {
    if (!productForm.name || productForm.price_inr <= 0) return;
    setSaveStatus("Saving product...");
    try {
      const isEdit = editingProductId !== null;
      const url = isEdit ? `${API_BASE}/api/merchant/products/${editingProductId}` : `${API_BASE}/api/merchant/products`;
      const method = isEdit ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(productForm)
      });

      if (res.ok) {
        fetchProducts();
        setShowProductModal(false);
        setEditingProductId(null);
        setProductForm({ name: "", category: "Protein", flavour: "Standard", price_inr: 2999, stock_count: 50, rating: 4.8, description: "", image_url: "" });
        setSaveStatus("Product Saved!");
        setTimeout(() => setSaveStatus(""), 3000);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Delete Product
  const handleDeleteProduct = async (id: number) => {
    if (!confirm("Are you sure you want to delete this product?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/merchant/products/${id}`, { method: "DELETE" });
      if (res.ok) fetchProducts();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col font-sans selection:bg-orange-500 selection:text-black">
      
      {/* Top Header */}
      <Header
        wallet={wallet}
        selectedLang={selectedLang}
        onSelectLang={setSelectedLang}
        cartCount={0}
        onOpenCart={() => {}}
        onOpenWallet={() => {}}
        isMerchantPage={true}
      />

      <div className="max-w-7xl mx-auto px-4 lg:px-8 py-8 flex-1 w-full space-y-8">
        
        {/* Banner */}
        <div className="glass-card bg-gradient-to-r from-orange-950/40 via-gray-900 to-gray-950 border border-orange-500/20 p-6 lg:p-8 rounded-3xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-bold text-orange-400 mb-1">
              <Store className="w-4 h-4" />
              <span>MERCHANT COMMAND CENTER</span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-black text-white tracking-tight">
              {config?.store_name || "MuscleBlaze Store Management"}
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Configure your multi-tenant catalog, voice AI sales executive, knowledge documents & order ledgers.
            </p>
          </div>

          <button
            onClick={() => {
              setEditingProductId(null);
              setProductForm({ name: "", category: "Protein", flavour: "Chocolate", price_inr: 3499, stock_count: 50, rating: 4.8, description: "", image_url: "" });
              setShowProductModal(true);
            }}
            className="py-3 px-5 rounded-2xl bg-gradient-to-r from-orange-500 to-amber-500 text-black font-extrabold text-xs shadow-lg shadow-orange-500/20 hover:opacity-90 transition-all flex items-center space-x-2 cursor-pointer active:scale-95"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            <span>Add New Product</span>
          </button>
        </div>

        {/* Tabs Navigation */}
        <div className="flex items-center space-x-2 border-b border-gray-800 pb-3 overflow-x-auto">
          {[
            { id: "products", label: "Product Catalog", icon: Package, count: products.length },
            { id: "config", label: "Voice Agent & Persona", icon: Settings },
            { id: "knowledge", label: "Knowledge Base Documents", icon: FileText },
            { id: "orders", label: "Live Orders Ledger", icon: Receipt, count: orders.length }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-2.5 px-4 rounded-xl text-xs font-extrabold transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? "bg-orange-500 text-black shadow-md shadow-orange-500/20"
                    : "text-gray-400 hover:text-white hover:bg-gray-900"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                    isActive ? "bg-black/20 text-black" : "bg-gray-800 text-gray-400"
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* TAB 1: PRODUCT CATALOG MANAGER */}
        {activeTab === "products" && (
          <div className="space-y-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-20 text-gray-400 space-x-2">
                <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
                <span className="text-xs font-medium">Loading catalog products...</span>
              </div>
            ) : products.length === 0 ? (
              <div className="glass-card p-12 text-center text-gray-400 space-y-3">
                <Package className="w-10 h-10 mx-auto text-gray-600" />
                <p className="font-bold text-sm">No products in merchant catalog.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {products.map((p) => (
                  <div key={p.id} className="glass-card p-5 rounded-2xl border border-gray-800 flex flex-col justify-between hover:border-gray-700 transition-all">
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] font-extrabold uppercase tracking-wider text-orange-400 bg-orange-500/10 px-2.5 py-1 rounded-md border border-orange-500/20">
                          {p.category}
                        </span>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => {
                              setEditingProductId(p.id);
                              setProductForm({
                                name: p.name,
                                category: p.category,
                                flavour: p.flavour,
                                price_inr: p.price_inr,
                                stock_count: p.stock_count,
                                rating: p.rating,
                                description: p.description || "",
                                image_url: p.image_url || ""
                              });
                              setShowProductModal(true);
                            }}
                            className="p-1.5 rounded-lg bg-gray-900 hover:bg-gray-800 text-gray-300 hover:text-white transition-colors cursor-pointer"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteProduct(p.id)}
                            className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <h3 className="font-extrabold text-base text-white mb-1 leading-snug">{p.name}</h3>
                      <p className="text-xs text-gray-400 line-clamp-2 mb-4">{p.description || "No description provided."}</p>
                    </div>

                    <div className="pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs">
                      <div>
                        <span className="text-[10px] text-gray-500 block uppercase">STORE PRICE</span>
                        <span className="font-black text-white text-base">₹{p.price_inr.toLocaleString("en-IN")}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-gray-500 block uppercase">STOCK COUNT</span>
                        <span className={`font-bold ${p.stock_count > 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {p.stock_count > 0 ? `${p.stock_count} Available` : "Out of Stock"}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: VOICE AGENT & PERSONA CONFIGURATOR */}
        {activeTab === "config" && config && (
          <div className="glass-card p-6 lg:p-8 rounded-3xl border border-gray-800 space-y-6 max-w-3xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div>
                <h3 className="font-extrabold text-lg text-white">Voice Agent & Store Persona Settings</h3>
                <p className="text-xs text-gray-400">Configure how Rohan (or your custom sales advisor) behaves and pitches products.</p>
              </div>
              {saveStatus && (
                <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-lg border border-emerald-500/20">
                  {saveStatus}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-gray-400 font-bold mb-1">Store Name</label>
                <input
                  type="text"
                  value={config.store_name}
                  onChange={(e) => setConfig({ ...config, store_name: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3.5 py-2.5 text-white font-semibold focus:border-orange-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-bold mb-1">Voice Agent Name</label>
                <input
                  type="text"
                  value={config.agent_name}
                  onChange={(e) => setConfig({ ...config, agent_name: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3.5 py-2.5 text-white font-semibold focus:border-orange-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-bold mb-1">Agent Personality Tone</label>
                <input
                  type="text"
                  value={config.agent_tone}
                  onChange={(e) => setConfig({ ...config, agent_tone: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3.5 py-2.5 text-white font-semibold focus:border-orange-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-bold mb-1">Active Coupon Code</label>
                <input
                  type="text"
                  value={config.active_coupon}
                  onChange={(e) => setConfig({ ...config, active_coupon: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3.5 py-2.5 text-orange-400 font-extrabold focus:border-orange-500 focus:outline-none"
                />
              </div>
            </div>

            <button
              onClick={handleSaveConfig}
              className="py-3 px-6 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-black font-extrabold text-xs shadow-lg hover:opacity-90 transition-all flex items-center space-x-2 cursor-pointer"
            >
              <Save className="w-4 h-4" />
              <span>Save Voice Agent Configuration</span>
            </button>
          </div>
        )}

        {/* TAB 3: KNOWLEDGE BASE DOCUMENTS */}
        {activeTab === "knowledge" && config && (
          <div className="glass-card p-6 lg:p-8 rounded-3xl border border-gray-800 space-y-6 max-w-3xl">
            <div>
              <h3 className="font-extrabold text-lg text-white">Product Specs & Brand Knowledge Base</h3>
              <p className="text-xs text-gray-400">Upload or edit product specification details, lab certifications, dosage rules, or warranty guidelines.</p>
            </div>

            <div>
              <label className="block text-gray-400 text-xs font-bold mb-2">Knowledge Context (Injected into LLM Prompts)</label>
              <textarea
                rows={6}
                value={config.knowledge_specs}
                onChange={(e) => setConfig({ ...config, knowledge_specs: e.target.value })}
                className="w-full bg-gray-900 border border-gray-800 rounded-2xl p-4 text-xs text-gray-200 font-mono focus:border-orange-500 focus:outline-none leading-relaxed"
                placeholder="Enter lab door certifications, dosage advice, warranty information..."
              />
            </div>

            <button
              onClick={handleSaveConfig}
              className="py-3 px-6 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-black font-extrabold text-xs shadow-lg hover:opacity-90 transition-all flex items-center space-x-2 cursor-pointer"
            >
              <Save className="w-4 h-4" />
              <span>Save Knowledge Base Specs</span>
            </button>
          </div>
        )}

        {/* TAB 4: LIVE ORDERS LEDGER */}
        {activeTab === "orders" && (
          <div className="space-y-4">
            <h3 className="font-extrabold text-lg text-white">Incoming Customer Voice Orders</h3>
            {orders.length === 0 ? (
              <div className="glass-card p-12 text-center text-gray-500">
                <Receipt className="w-10 h-10 mx-auto mb-2 text-gray-600" />
                <p className="text-xs">No orders recorded in live registry yet.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {orders.map((o) => (
                  <div key={o.order_id} className="glass-card p-5 rounded-2xl border border-gray-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
                    <div>
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="font-black text-white text-sm">{o.order_id}</span>
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                          o.status === "ORDER_CONFIRMED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>
                          {o.status}
                        </span>
                      </div>
                      <p className="text-gray-400 font-medium">Customer: <strong className="text-gray-200">{o.customer_name}</strong> • Date: {o.created_at}</p>
                      {o.delivery_address && (
                        <p className="text-gray-400 mt-1">Address: <span className="text-gray-300">{o.delivery_address}</span></p>
                      )}
                    </div>

                    <div className="text-left md:text-right">
                      <span className="text-[10px] text-gray-500 uppercase block">TOTAL VALUE</span>
                      <span className="font-black text-orange-400 text-lg">₹{o.quote?.final_total ? o.quote.final_total.toLocaleString("en-IN") : "0"}</span>
                      {o.razorpay_payment_link && (
                        <a
                          href={o.razorpay_payment_link}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center space-x-1 text-emerald-400 hover:underline mt-1 font-bold text-[11px]"
                        >
                          <span>Razorpay Link</span>
                          <ArrowUpRight className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </div>

      {/* Add / Edit Product Modal */}
      {showProductModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
          <div className="w-full max-w-lg glass-card bg-gray-950 border border-gray-800 rounded-3xl p-6 lg:p-8 shadow-2xl relative space-y-4">
            <h3 className="font-black text-lg text-white">
              {editingProductId ? "Edit Product" : "Add New Merchant Product"}
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 font-bold mb-1">Product Name</label>
                <input
                  type="text"
                  value={productForm.name}
                  onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                  placeholder="e.g. MuscleBlaze Biozyme Whey 2kg"
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-semibold focus:border-orange-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-400 font-bold mb-1">Category</label>
                  <input
                    type="text"
                    value={productForm.category}
                    onChange={(e) => setProductForm({ ...productForm, category: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-semibold focus:border-orange-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 font-bold mb-1">Price (INR)</label>
                  <input
                    type="number"
                    value={productForm.price_inr}
                    onChange={(e) => setProductForm({ ...productForm, price_inr: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-semibold focus:border-orange-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-400 font-bold mb-1">Stock Units</label>
                  <input
                    type="number"
                    value={productForm.stock_count}
                    onChange={(e) => setProductForm({ ...productForm, stock_count: parseInt(e.target.value) || 0 })}
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-semibold focus:border-orange-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 font-bold mb-1">Flavour / Variant</label>
                  <input
                    type="text"
                    value={productForm.flavour}
                    onChange={(e) => setProductForm({ ...productForm, flavour: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-semibold focus:border-orange-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-gray-400 font-bold mb-1">Description</label>
                <textarea
                  rows={2}
                  value={productForm.description}
                  onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-semibold focus:border-orange-500 focus:outline-none text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-gray-800">
              <button
                onClick={() => setShowProductModal(false)}
                className="py-2 px-4 rounded-xl bg-gray-900 hover:bg-gray-800 text-gray-300 font-bold text-xs cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProduct}
                className="py-2 px-5 rounded-xl bg-orange-500 text-black font-extrabold text-xs hover:bg-orange-400 transition-all cursor-pointer"
              >
                Save Product
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
