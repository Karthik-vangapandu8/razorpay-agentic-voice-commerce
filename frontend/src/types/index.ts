export interface Product {
  id: number;
  name: string;
  category: string;
  flavour: string;
  price_inr: number;
  discount_price: number;
  stock_count: number;
  rating: number;
  description: string;
  image_url: string;
}

export interface PricingLineItem {
  product_id: number;
  name: string;
  unit_price: number;
  quantity: number;
  line_total: number;
  flavour?: string;
}

export interface CartQuote {
  items: PricingLineItem[];
  subtotal: number;
  combo_discount: number;
  coupon_code?: string;
  coupon_discount: number;
  total_discount: number;
  free_gifts: string[];
  final_total: number;
  is_valid: boolean;
  error_message?: string;
}

export interface WalletTransaction {
  tx_id: string;
  amount: number;
  tx_type: string;
  reference_id?: string;
  description: string;
  timestamp: string;
}

export interface WalletInfo {
  wallet_id: string;
  customer_name: string;
  balance: number;
  currency: string;
  daily_spend_limit: number;
  remaining_daily_limit: number;
  kya_verified: boolean;
  transactions: WalletTransaction[];
}

export interface OrderResult {
  status: string;
  order_id: string;
  order_status: string;
  customer: string;
  total_amount: string;
  wallet_paid: string;
  razorpay_pending: string;
  razorpay_payment_link?: string;
  free_gifts: string[];
  receipt_file?: string;
}

export interface ChatResponse {
  transcript: string;
  language_code: string;
  assistant_text: string;
  audio_base64: string;
  highlighted_products: Partial<Product>[];
  active_quote?: CartQuote;
  order_result?: OrderResult;
}
