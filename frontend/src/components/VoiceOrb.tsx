"use client";

import React, { useState, useRef, useEffect } from "react";
import { Mic, MicOff, Send, Volume2, Sparkles, Loader2, Bot } from "lucide-react";

interface VoiceOrbProps {
  isSpeaking: boolean;
  isListening: boolean;
  isThinking: boolean;
  transcript: string;
  assistantText: string;
  onStartRecord: () => void;
  onStopRecord: () => void;
  onSendText: (text: string) => void;
  onPlayAudio?: () => void;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  isSpeaking,
  isListening,
  isThinking,
  transcript,
  assistantText,
  onStartRecord,
  onStopRecord,
  onSendText,
  onPlayAudio,
}) => {
  const [inputText, setInputText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isThinking) return;
    onSendText(inputText);
    setInputText("");
  };

  return (
    <div className="glass-card rounded-2xl p-6 lg:p-8 max-w-4xl mx-auto shadow-2xl relative overflow-hidden border border-gray-800">
      
      {/* Background Ambient Glow */}
      <div className={`absolute -top-24 -left-24 w-72 h-72 rounded-full blur-3xl transition-opacity duration-700 pointer-events-none ${
        isSpeaking ? "bg-orange-500/25 opacity-100" : isListening ? "bg-emerald-500/25 opacity-100" : "bg-orange-500/10 opacity-40"
      }`} />
      
      <div className="relative z-10 flex flex-col items-center text-center">

        {/* AI Voice Orb Container */}
        <div className="relative mb-6">
          
          {/* Outer Pulsing Rings */}
          {isSpeaking && (
            <div className="absolute inset-0 rounded-full bg-orange-500/30 pulse-ring pointer-events-none" />
          )}
          {isListening && (
            <div className="absolute inset-0 rounded-full bg-emerald-500/30 pulse-ring pointer-events-none" />
          )}

          {/* Main Interactive Button / Orb */}
          <button
            onClick={isListening ? onStopRecord : onStartRecord}
            disabled={isThinking}
            className={`w-28 h-28 lg:w-32 lg:h-32 rounded-full flex flex-col items-center justify-center transition-all duration-300 transform active:scale-95 cursor-pointer shadow-2xl relative z-10 ${
              isSpeaking
                ? "bg-gradient-to-tr from-amber-500 via-orange-600 to-red-600 shadow-orange-500/50 glow-orange"
                : isListening
                ? "bg-gradient-to-tr from-emerald-500 to-teal-600 shadow-emerald-500/50 glow-green animate-pulse"
                : isThinking
                ? "bg-gray-800 border-2 border-orange-500/40"
                : "bg-gradient-to-tr from-gray-900 via-gray-800 to-gray-900 border border-gray-700 hover:border-orange-500/50 hover:shadow-orange-500/20"
            }`}
          >
            {isThinking ? (
              <Loader2 className="w-10 h-10 text-orange-400 animate-spin" />
            ) : isListening ? (
              <Mic className="w-10 h-10 text-white animate-bounce" />
            ) : isSpeaking ? (
              <Volume2 className="w-10 h-10 text-white animate-pulse" />
            ) : (
              <Bot className="w-10 h-10 text-orange-400 group-hover:scale-110 transition-transform" />
            )}

            <span className="text-[10px] font-extrabold uppercase tracking-wider mt-1 text-white/90">
              {isThinking ? "Thinking" : isListening ? "Listening" : isSpeaking ? "Rohan Speaking" : "Tap to Speak"}
            </span>
          </button>

          {/* Soundwave Animated Bars */}
          {(isListening || isSpeaking) && (
            <div className="flex items-center justify-center space-x-1.5 mt-4">
              {[1, 2, 3, 4, 5, 6, 7].map((bar) => (
                <div
                  key={bar}
                  className={`w-1 rounded-full soundwave-bar ${
                    isListening ? "bg-emerald-400" : "bg-orange-400"
                  }`}
                  style={{
                    animationDelay: `${bar * 0.15}s`,
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Live Status Badge */}
        <div className="mb-4">
          <span className={`inline-flex items-center space-x-2 text-xs font-semibold px-3 py-1 rounded-full border ${
            isSpeaking
              ? "bg-orange-500/20 text-orange-400 border-orange-500/30"
              : isListening
              ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
              : isThinking
              ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
              : "bg-gray-800 text-gray-400 border-gray-700"
          }`}>
            <Sparkles className="w-3.5 h-3.5" />
            <span>
              {isSpeaking
                ? "AI Advisor Rohan is answering..."
                : isListening
                ? "Microphone Active — Speak your goals or items"
                : isThinking
                ? "Querying Groq LPU & Store Database..."
                : "Ask about proteins, prices, coupons ('FIT10'), or combos!"}
            </span>
          </span>
        </div>

        {/* Real-Time Subtitles & Transcript Caption Box */}
        {(assistantText || transcript) && (
          <div className="w-full bg-gray-900/90 rounded-xl p-4 mb-6 text-left border border-gray-800 backdrop-blur-md shadow-inner">
            {transcript && (
              <div className="mb-2">
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">You Said:</span>
                <p className="text-xs text-gray-300 font-medium italic">&ldquo;{transcript}&rdquo;</p>
              </div>
            )}
            {assistantText && (
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-orange-400 uppercase tracking-wider flex items-center space-x-1">
                    <span>Rohan (AI Advisor):</span>
                  </span>
                  {onPlayAudio && (
                    <button
                      onClick={onPlayAudio}
                      className="glass-pill bg-orange-500/20 hover:bg-orange-500/30 text-orange-400 text-[10px] font-bold px-2 py-0.5 rounded-md border border-orange-500/40 flex items-center space-x-1 cursor-pointer transition-all"
                    >
                      <Volume2 className="w-3 h-3" />
                      <span>Play Voice</span>
                    </button>
                  )}
                </div>
                <p className="text-sm lg:text-base text-white font-medium leading-relaxed mt-0.5">
                  {assistantText}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Fallback Text Input Form */}
        <form onSubmit={handleSubmit} className="w-full flex items-center space-x-2 max-w-xl">
          <input
            ref={inputRef}
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Or type here e.g. 'Biozyme Whey 2kg pack kar do, FIT10 coupon'..."
            disabled={isThinking}
            className="flex-1 glass-pill bg-gray-900/80 text-white placeholder-gray-500 text-xs lg:text-sm px-4 py-2.5 rounded-xl border border-gray-700 focus:outline-none focus:border-orange-500 transition-colors"
          />
          <button
            type="submit"
            disabled={isThinking || !inputText.trim()}
            className="bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-black font-extrabold px-4 py-2.5 rounded-xl transition-all flex items-center space-x-1 cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>

      </div>
    </div>
  );
};
