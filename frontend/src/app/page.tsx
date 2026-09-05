"use client";

import React, { useState, useEffect, useRef } from "react";
import { Header } from "@/components/Header";
import { VoiceOrb } from "@/components/VoiceOrb";
import { ProductCard } from "@/components/ProductCard";
import { CartDrawer } from "@/components/CartDrawer";
import { WalletModal } from "@/components/WalletModal";
import { Product, CartQuote, OrderResult, WalletInfo, ChatResponse } from "@/types";
import { Sparkles, Dumbbell, Zap, Flame, ShieldAlert, Award, RotateCcw, Filter } from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function Home() {
  const [catalog, setCatalog] = useState<Product[]>([]);
  const [filteredCatalog, setFilteredCatalog] = useState<Product[] | null>(null);
  const [searchReason, setSearchReason] = useState<string>("");
  const [wallet, setWallet] = useState<WalletInfo | null>(null);
  const [cart, setCart] = useState<Product[]>([]);
  const [selectedLang, setSelectedLang] = useState<string>("hi-IN");
  
  // Voice & AI State
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>("");
  const [assistantText, setAssistantText] = useState<string>("");
  const [highlightedNames, setHighlightedNames] = useState<string[]>([]);
  const [quote, setQuote] = useState<CartQuote | null>(null);
  const [orderResult, setOrderResult] = useState<OrderResult | null>(null);

  // UI Modals & Drawers
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [isWalletOpen, setIsWalletOpen] = useState<boolean>(false);
  const [isProcessingCheckout, setIsProcessingCheckout] = useState<boolean>(false);

  // Audio Recording, VAD & Playback refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const vadIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const recordingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [customerName, setCustomerName] = useState<string>("Kartik");

  // Fetch initial catalog, wallet info, and proactive greeting
  useEffect(() => {
    fetchCatalog();
    fetchWallet();
    fetchInitialGreeting();
  }, []);

  const fetchCatalog = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/catalog`);
      if (res.ok) {
        const data = await res.json();
        setCatalog(data.catalog || []);
      }
    } catch (e) {
      console.error("Failed to fetch catalog:", e);
    }
  };

  const fetchWallet = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/wallet?customer_name=${encodeURIComponent(customerName)}`);
      if (res.ok) {
        const data = await res.json();
        setWallet(data);
      }
    } catch (e) {
      console.error("Failed to fetch wallet info:", e);
    }
  };

  const fetchInitialGreeting = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/greeting?lang_code=${selectedLang}`);
      if (res.ok) {
        const data = await res.json();
        if (data.greeting_text) setAssistantText(data.greeting_text);
        if (data.audio_base64) {
          playAudioBase64(data.audio_base64);
        }
      }
    } catch (e) {
      console.error("Failed to fetch initial greeting:", e);
    }
  };

  const playAudioBase64 = (base64Audio: string) => {
    if (!base64Audio) return;
    try {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }

      const audioSrc = `data:audio/wav;base64,${base64Audio}`;
      const audio = new Audio(audioSrc);
      currentAudioRef.current = audio;

      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = (err) => {
        console.error("Audio playback error:", err);
        setIsSpeaking(false);
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          console.warn("Autoplay blocked by browser. User interaction needed:", err);
          setIsSpeaking(false);
        });
      }
    } catch (e) {
      console.error("Audio initialization exception:", e);
      setIsSpeaking(false);
    }
  };

  const startRecording = async () => {
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (audioBlob.size > 0) {
          const extension = mediaRecorder.mimeType.includes("webm") ? "webm" : "wav";
          sendVoiceChat(audioBlob, `user_voice.${extension}`);
        } else {
          console.warn("Recorded audio blob is empty (0 bytes).");
        }
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start(250);
      setIsListening(true);

      // Web Audio API Silence VAD (Auto-stop after 1.2s of silence)
      try {
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioContext;
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        let silenceStart = Date.now();
        let hasSpoken = false;

        if (vadIntervalRef.current) clearInterval(vadIntervalRef.current);
        vadIntervalRef.current = setInterval(() => {
          if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== "recording") return;

          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          const average = sum / bufferLength;

          // Speech threshold (volume level >= 10)
          if (average >= 10) {
            hasSpoken = true;
            silenceStart = Date.now();
          } else {
            // If user has spoken and then pauses for 1.2s (1200ms)
            if (hasSpoken && (Date.now() - silenceStart > 1200)) {
              console.log("🎙️ VAD Auto-Stop: 1.2s silence detected.");
              stopRecording();
            }
          }
        }, 100);
      } catch (vadErr) {
        console.warn("Web Audio VAD initialization error:", vadErr);
      }

      if (recordingTimeoutRef.current) clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
          stopRecording();
        }
      }, 20000);
    } catch (err) {
      console.error("Microphone access error:", err);
      alert("Microphone access is required for voice chat!");
    }
  };

  const stopRecording = () => {
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setIsListening(false);
    }
  };

  const [sessionId, setSessionId] = useState<string>(() => "sess_" + Date.now());

  const sendVoiceChat = async (audioBlob: Blob, filename: string = "user_voice.webm") => {
    setIsThinking(true);
    const formData = new FormData();
    formData.append("file", audioBlob, filename);
    formData.append("session_id", sessionId);
    formData.append("customer_name", customerName);

    try {
      const res = await fetch(`${API_BASE}/api/voice-chat`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data: ChatResponse = await res.json();
        handleServerResponse(data);
      }
    } catch (e) {
      console.error("Voice chat error:", e);
    } finally {
      setIsThinking(false);
    }
  };

  const sendTextChat = async (text: string) => {
    setIsThinking(true);
    setTranscript(text);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          customer_name: customerName,
          text,
          language_code: selectedLang,
        }),
      });

      if (res.ok) {
        const data: ChatResponse = await res.json();
        handleServerResponse(data);
      }
    } catch (e) {
      console.error("Text chat error:", e);
    } finally {
      setIsThinking(false);
    }
  };

  // Handle Response from API Server
  const handleServerResponse = (data: ChatResponse) => {
    if (data.transcript) {
      setTranscript(data.transcript);
      setSearchReason(data.transcript);
    }
    if (data.assistant_text) setAssistantText(data.assistant_text);
    if (data.audio_base64) playAudioBase64(data.audio_base64);

    // Filter and highlight recommended products based on user's question/goal
    if (data.highlighted_products && data.highlighted_products.length > 0) {
      const names = data.highlighted_products.map((p) => p.name || "").filter(Boolean);
      setHighlightedNames(names);

      // Match against full catalog items
      const matchedProducts: Product[] = [];
      data.highlighted_products.forEach((hp) => {
        const hpName = (hp.name || "").toLowerCase();
        const match = catalog.find((catItem) => 
          catItem.name.toLowerCase().includes(hpName) ||
          hpName.includes(catItem.name.toLowerCase()) ||
          (hp.id && catItem.id === hp.id)
        );
        if (match && !matchedProducts.some((m) => m.id === match.id)) {
          matchedProducts.push(match);
        } else if (!match && hp.id && hp.name && hp.price_inr) {
          // Construct full product object from hp
          matchedProducts.push({
            id: hp.id,
            name: hp.name,
            category: hp.category || "Supplements",
            flavour: hp.flavour || "Chocolate",
            price_inr: hp.price_inr || 4499,
            stock_count: hp.stock_count || 20,
            rating: hp.rating || 4.8,
            description: hp.description || "Premium certified supplement",
            image_url: hp.image_url || "https://images.unsplash.com/photo-1579722821273-0f6c7d44362f?auto=format&fit=crop&w=600&q=80",
            discount_price: hp.discount_price || round((hp.price_inr || 4499) * 0.9)
          });
        }
      });

      if (matchedProducts.length > 0) {
        setFilteredCatalog(matchedProducts);
      }
      
      // Auto-add highlighted product to cart if not present
      data.highlighted_products.forEach((hp) => {
        const match = catalog.find((catItem) => catItem.name.toLowerCase().includes((hp.name || "").toLowerCase()));
        if (match && !cart.some((c) => c.id === match.id)) {
          setCart((prev) => [...prev, match]);
        }
      });
    }

    if (data.active_quote) {
      setQuote(data.active_quote);
    }

    if (data.order_result) {
      setOrderResult(data.order_result);
      setIsCartOpen(true);
      fetchWallet();
    }
  };

  const handleAddToCart = (product: Product) => {
    if (!cart.some((c) => c.id === product.id)) {
      const updatedCart = [...cart, product];
      setCart(updatedCart);
      updateCartQuote(updatedCart);
    }
  };

  const handleRemoveFromCart = (productId: number) => {
    const updatedCart = cart.filter((item) => item.id !== productId);
    setCart(updatedCart);
    updateCartQuote(updatedCart);
  };

  const updateCartQuote = (items: Product[]) => {
    if (items.length === 0) {
      setQuote(null);
      return;
    }
    let subtotal = 0;
    items.forEach((i) => (subtotal += i.price_inr));
    const discount = round(subtotal * 0.1);
    setQuote({
      items: items.map((i) => ({ product_id: i.id, name: i.name, unit_price: i.price_inr, quantity: 1, line_total: i.price_inr })),
      subtotal,
      combo_discount: items.length >= 2 ? 300 : 0,
      coupon_code: "FIT10",
      coupon_discount: discount,
      total_discount: discount + (items.length >= 2 ? 300 : 0),
      free_gifts: subtotal > 1999 ? ["MuscleBlaze Premium Shaker Bottle (Free)"] : [],
      final_total: Math.max(0, subtotal - discount - (items.length >= 2 ? 300 : 0)),
      is_valid: true,
    });
  };

  function round(num: number) {
    return Math.round(num * 100) / 100;
  }

  const handleCheckoutWallet = async () => {
    setIsProcessingCheckout(true);
    const itemReqs = cart.map((c) => ({ product_name: c.name, quantity: 1 }));
    try {
      const res = await fetch(`${API_BASE}/api/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: customerName,
          items: itemReqs,
          coupon_code: "FIT10",
          pay_via_wallet: true,
        }),
      });
      if (res.ok) {
        const data: OrderResult = await res.json();
        setOrderResult(data);
        fetchWallet();
      }
    } catch (e) {
      console.error("Wallet checkout error:", e);
    } finally {
      setIsProcessingCheckout(false);
    }
  };

  const handleCheckoutRazorpay = async () => {
    setIsProcessingCheckout(true);
    const itemReqs = cart.map((c) => ({ product_name: c.name, quantity: 1 }));
    try {
      const res = await fetch(`${API_BASE}/api/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: customerName,
          items: itemReqs,
          coupon_code: "FIT10",
          pay_via_wallet: false,
        }),
      });
      if (res.ok) {
        const data: OrderResult = await res.json();
        setOrderResult(data);
      }
    } catch (e) {
      console.error("Razorpay checkout error:", e);
    } finally {
      setIsProcessingCheckout(false);
    }
  };

  const displayProducts = filteredCatalog && filteredCatalog.length > 0 ? filteredCatalog : catalog;

  return (
    <div className="min-h-screen bg-[#0b0c10] text-gray-100 flex flex-col justify-between selection:bg-orange-500 selection:text-black">
      
      {/* Header */}
      <Header
        wallet={wallet}
        selectedLang={selectedLang}
        onSelectLang={(lang) => {
          setSelectedLang(lang);
          fetchInitialGreeting();
        }}
        cartCount={cart.length}
        onOpenCart={() => setIsCartOpen(true)}
        onOpenWallet={() => setIsWalletOpen(true)}
      />

      {/* Main Content Body */}
      <main className="max-w-7xl mx-auto px-4 lg:px-8 py-8 flex-1 space-y-10 w-full">
        
        {/* Section 1: Hero Voice AI Assistant */}
        <section>
          <VoiceOrb
            isSpeaking={isSpeaking}
            isListening={isListening}
            isThinking={isThinking}
            transcript={transcript}
            assistantText={assistantText}
            onStartRecord={startRecording}
            onStopRecord={stopRecording}
            onSendText={sendTextChat}
          />
        </section>

        {/* Section 2: Synchronous Product Catalog Grid */}
        <section>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-xl lg:text-2xl font-black text-white flex items-center space-x-2">
                {filteredCatalog ? (
                  <>
                    <Sparkles className="w-6 h-6 text-orange-500 fill-orange-500 animate-pulse" />
                    <span>RECOMMENDED FOR YOUR QUESTION</span>
                  </>
                ) : (
                  <>
                    <Flame className="w-6 h-6 text-orange-500 fill-orange-500" />
                    <span>RECOMMENDED SUPPLEMENT STACK</span>
                  </>
                )}
              </h2>
              <p className="text-xs text-gray-400">
                {filteredCatalog
                  ? `Displaying ${filteredCatalog.length} product(s) dynamically matched by Rohan for: "${searchReason || transcript}"`
                  : "Products highlighted in real-time as Rohan speaks"}
              </p>
            </div>

            <div className="flex items-center space-x-3">
              {filteredCatalog && (
                <button
                  onClick={() => {
                    setFilteredCatalog(null);
                    setSessionId("sess_" + Date.now());
                  }}
                  className="text-xs font-bold text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-full border border-gray-700 flex items-center space-x-1.5 transition-all cursor-pointer shadow-md"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-orange-400" />
                  <span>Show All Products ({catalog.length})</span>
                </button>
              )}
              <div className="hidden sm:flex items-center space-x-2 text-xs text-emerald-400 font-bold bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
                <Award className="w-4 h-4" />
                <span>Labdoor USA Certified Products</span>
              </div>
            </div>
          </div>

          <div className={displayProducts.length === 1 ? "max-w-md mx-auto" : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"}>
            {displayProducts.map((product) => {
              const isHL = highlightedNames.some((n) => product.name.toLowerCase().includes(n.toLowerCase()));
              const inCart = cart.some((c) => c.id === product.id);
              return (
                <ProductCard
                  key={product.id}
                  product={product}
                  isHighlighted={isHL || displayProducts.length === 1}
                  isInCart={inCart}
                  onAddToCart={handleAddToCart}
                />
              );
            })}
          </div>
        </section>

      </main>

      {/* Drawers & Modals */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        cart={cart}
        onRemoveFromCart={handleRemoveFromCart}
        quote={quote}
        orderResult={orderResult}
        wallet={wallet}
        onCheckoutWallet={handleCheckoutWallet}
        onCheckoutRazorpay={handleCheckoutRazorpay}
        isProcessing={isProcessingCheckout}
      />

      <WalletModal
        isOpen={isWalletOpen}
        onClose={() => setIsWalletOpen(false)}
        wallet={wallet}
        onTopUpSuccess={fetchWallet}
      />

      {/* Footer */}
      <footer className="glass-card border-t border-gray-800 py-6 text-center text-xs text-gray-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between px-4 lg:px-8 space-y-2 sm:space-y-0">
          <p>© 2026 Sauda AI • Universal Agentic Voice Commerce Platform (Powered by Sarvam AI & Groq LPU)</p>
          <div className="flex items-center space-x-4">
            <span className="text-emerald-400 font-semibold">Razorpay Test Mode Active</span>
            <span>•</span>
            <span className="text-orange-400 font-semibold">KYA Verified</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
