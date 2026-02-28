# Arke API Reference

Two namespaces discovered: **`sales-api`** and **`supply-api`**.

---

## Common Types

### Audit Fields (present on most detail types)
```ts
{
  archived?: boolean;
  created?: { at: string; by: { full_name: string; id: string; username: string } };
  updated?: { at: string; by: { full_name: string; id: string; username: string } };
  custom_form_values?: { generation?: number; values?: (fieldDef & { value?: unknown })[] };
  foreign_ids?: Record<string, unknown>;
  notes?: string;
  version: number;
}
```

### Price
```ts
{
  base_price?: number;
  currency: "EUR" | "USD" | "GBP";
  unit: number;
  vat?: number;
  discount_percent?: number;
  deals?: { category?: string; min_quantity: number; unit: number }[];
}
```

### Company / Supplier / Customer attr snapshot
```ts
{ address?: string; country?: string; id?: string; name: string; vat: string }
```

### Warehouse attr snapshot
```ts
{ id: string; name: string; supplier_id?: string }
```

### Order line item (shared shape)
```ts
{
  extra_id: string;        // required external line ID
  name: string;
  quantity: number;
  uom: string;
  id?: string;
  item_id?: string;
  lot?: string;
  external_lot?: string;
  order_id?: string;
  prices?: Price;
  meta?: Record<string, unknown>;
}
```

---

## sales-api

Base path: `/` (tenant-scoped)

### Orders

| Method | Path | Operation | Description |
|--------|------|-----------|-------------|
| `GET`  | `/order` | `listOrders` | List all sales orders |
| `GET`  | `/order/_active` | `listActiveOrders` | List active orders (with product lines) |
| `GET`  | `/order/_last_two_month_sales` | `lastTwoMonthSales` | Monthly sales totals for last 2 months |
| `GET`  | `/order/{orderId}` | `showOrder` | Get full order details |
| `PUT`  | `/order` | `createOrder` | Create a sales order |
| `POST` | `/order/{orderId}/_accept` | `acceptOrder` | Accept/confirm an order |
| `POST` | `/order/{orderId}/_update-priority` | `updateOrderPriority` | Change order priority |
| `POST` | `/order/{orderId}/_update-sales-channel` | `updateOrderSalesChannel` | Reassign sales channel |

#### `orderSummary`
```ts
interface orderSummary {
  id?: string;
  internal_id?: string;         // e.g. "SO-2024-001"
  status: "draft" | "accepted" | "sent";
  time?: string;
  expected_shipping_time: string;
  external_id?: string;
  priority?: number;            // 1–5, lower = higher priority, default 3
  total_vat_incl: number;
  default_currency?: string;
  shipped?: "completed" | "not shipped" | "partial";
  customer_attr?: CompanyAttr;
  sales_channel_attr?: { extra_id?: string; id: string; name: string };
}
```

#### `orderDetails` (extends orderSummary + audit)
```ts
{
  customer_id: string;
  shipping_address: string;
  total: number;
  products: OrderLineItem[];
  payment_method?: string;
  agent?: UserRef;
  proxy?: CompanyAttr;
  proxy_agent?: UserRef;
  quote_internal_id?: string;
  sales_channel_id?: string;
  supplier_attr?: CompanyAttr;
}
```

#### `activeOrder` (extends orderSummary)
```ts
{ products: activeOrderProduct[] }
```

#### `monthlySales`
```ts
interface monthlySales { month: string; order_count: number; total: number; }
```

---

### Quotes

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/order/{orderId}/quote` | `listQuotesByOrder` |
| `PUT`  | `/order/{orderId}/quote` | `createQuoteByOrder` |
| `GET`  | `/order/{orderId}/quote/{quoteId}` | `showQuote` |
| `POST` | `/order/{orderId}/quote/{quoteId}/_reject` | `rejectQuote` |

#### `quoteSummary`
```ts
interface quoteSummary {
  id?: string;
  internal_id?: string;
  status: "draft" | "sent" | "accepted" | "rejected";
  time?: string;
  sales_channel_attr?: { extra_id?: string; id: string; name: string };
}
```

#### `quoteDetails` (extends quoteSummary + audit)
```ts
{
  order_id: string;
  customer_id?: string;
  customer_attr?: CompanyAttr;
  shipping_address: string;
  expected_shipping_time: string;
  expires_at: string;
  total: number;
  total_vat_incl: number;
  products: OrderLineItem[];
  payment_method?: string;
  default_currency?: string;
  external_id?: string;
  sales_channel_id?: string;
  supplier_attr?: CompanyAttr;
}
```

---

### Customers

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/customer` | `listCustomers` |
| `GET`  | `/customer/_lookup` | `lookupCustomer` |
| `GET`  | `/customer/{customerId}` | `showCustomer` |
| `PUT`  | `/customer` | `createCustomer` |
| `PUT`  | `/customer/{customerId}` | `updateCustomer` |

#### `customerSummary`
```ts
interface customerSummary {
  id?: string;
  name: string;
  vat_no: string;
  default_currency: string;
  categories: string[];
  emails: { email: string; name: string }[];
  phones: { name: string; phone: string }[];
}
```

#### `customerDetails` (extends customerSummary + audit)
```ts
{
  addresses: { address: string; country: string; name: string }[];
  agent?: UserRef;
  contact_name?: string;
  description?: string;
  preferred_payment_method?: string;
  website?: string;
}
```

---

### Customer Pricing

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/customer/{customerId}/price-list` | `listCustomerPrices` |
| `POST` | `/customer/{customerId}/price-list` | `addCustomerPrice` |
| `PUT`  | `/customer/{customerId}/price-list/{productId}` | `updateCustomerPrice` |
| `DELETE` | `/customer/{customerId}/price-list/{productId}` | `deleteCustomerPrice` |
| `POST` | `/customer/{customerId}/products/{productId}/_calculate-price` | `calculatePrice` |
| `GET`  | `/customer/{customerId}/offer/_price-list` | `getCustomerPriceList` |

#### `customerProductPrice`
```ts
interface customerProductPrice {
  internal_id: string;
  product_id: string;
  product_name: string;
  price: Price;
  created_at?: string;
  updated_at?: string;
}
```

#### `calculatePriceRequest`
```ts
interface calculatePriceRequest {
  quantity?: number;
  applicable_price?: number;    // skip pricing lookup if provided
  discount_percent?: number;    // mutually exclusive with final_price
  final_price?: number;         // mutually exclusive with discount_percent
  affiliate_customer_id?: string;
}
```

#### `calculatePriceResult`
```ts
interface calculatePriceResult {
  applicable_price: number;
  final_price: number;
  discount_percent: number;
  discount_amount: number;
  margin_percent?: number;      // null if no purchase cost available
  price_source?: priceSource;
  applied_offer?: offerPriceDetail;
}
```

---

### Offers

| Method | Path | Operation |
|--------|------|-----------|
| `PUT`  | `/customer/{customerId}/offer` | `createOffer` |

#### `offerDetails` (extends offerSummary + audit)
```ts
{ products: OrderLineItem[] }
```

---

### Sales Channels

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/sales-channel` | `listSalesChannels` |
| `GET`  | `/sales-channel/{salesChannelId}` | `showSalesChannel` |
| `PUT`  | `/sales-channel` | `createSalesChannel` |
| `PUT`  | `/sales-channel/{salesChannelId}` | `updateSalesChannel` |

#### `salesChannelSummary`
```ts
interface salesChannelSummary {
  id?: string;
  name: string;
  status: "active" | "inactive";
  type: "b2b" | "e-commerce";
}
```

---

### Settings

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/settings` | `showSettings` |
| `PUT`  | `/settings` | `updateSettings` |
| `GET`  | `/settings/custom-form/{domainObject}` | `showCustomForm` |

#### `settings`
```ts
{ agents?: boolean; offers?: boolean; templates: templates_attr }
```

---

### Admin

| Method | Path | Operation |
|--------|------|-----------|
| `POST` | `/admin/tenant/{tenantId}/_wipe` | `adminWipeTenant` |

---

## supply-api

### Purchase Orders

| Method | Path | Operation | Description |
|--------|------|-----------|-------------|
| `GET`  | `/order` | `listOrders` | List purchase orders |
| `GET`  | `/order/_active` | `listActiveOrders` | List active purchase orders |
| `GET`  | `/supplier/{supplierId}/order` | `listOrdersBySupplier` | Orders for a specific supplier |
| `PUT`  | `/order` | `createOrder` | Create a purchase order |
| `POST` | `/order/_createBulk` | `createBulkOrder` | Bulk create orders from raw material IDs |
| `PUT`  | `/order/{orderId}` | `updateOrder` | Update an order |
| `POST` | `/order/{orderId}/_send` | `sendOrder` | Send order to supplier (email) |
| `POST` | `/order/{orderId}/_accept` | `acceptOrder` | Mark order as accepted by supplier |

#### `orderSummary` (supply-api)
```ts
interface orderSummary {
  id?: string;
  internal_id?: string;         // e.g. "PO-2024-001"
  name: string;
  status: "draft" | "sent" | "accepted" | "shipped" | "rejected";
  time?: string;
  expected_delivery_time: string;
  total_vat_incl: number;
  default_currency?: string;
  shipment?: "not received" | "partial" | "received";
  supplier_attr?: CompanyAttr;
  warehouse_attr?: WarehouseAttr;
  warehouse_id?: string;
  buckets?: rawMaterialInventoryBuckets;
}
```

#### `orderDetails` (extends orderSummary + audit)
```ts
{
  supplier_id: string;
  supplier?: supplierSummary;
  shipping_address: string;
  payment_method: string;
  total: number;
  buyer_attr?: CompanyAttr;
  raw_materials: OrderLineItem[];
}
```

#### `sendOrderCommand`
```ts
interface sendOrderCommand {
  dry_run: boolean;
  email_body?: string;
  recipient?: string;
}
```

#### `bulkOrderDetails`
```ts
interface bulkOrderDetails { raw_material_id: string; quantity: number; }
```

---

### Suppliers

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/supplier/_self` | `showSelfSupplier` |
| `GET`  | `/supplier/{supplierId}` | `showSupplier` |
| `GET`  | `/supplier/_categories` | `listSupplierCategories` |

#### `supplierDetails` (extends supplierSummary + audit)
```ts
{
  addresses: { address: string; country: string; name: string }[];
  bank: { iban?: string; name?: string; swift?: string };
  contact_name?: string;
  description?: string;
  payment_method?: string;
  website?: string;
}
```

---

### Raw Materials

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/supplier/{supplierId}/raw-material` | `listRawMaterialsBySupplier` |

#### `rawMaterialSummary`
```ts
interface rawMaterialSummary {
  id?: string;
  external_id: string;
  name: string;
  categories: string[];
  uom: string;
  minimum_quantity: number;
  supplier_id: string;
  supplier_attr?: CompanyAttr;
  prices?: Price;
  lead_time?: string;
  description?: string;
  prod_id?: string;
  purchasable_product_id?: string;
  aggregate_of_id?: string;
  aggregate_quantity?: number;
  created?: AuditRef;
}
```

---

### Inventory

| Method | Path | Operation |
|--------|------|-----------|
| `GET`  | `/inventory/raw-material` | `groupedListRawMaterialInventoryItems` |
| `GET`  | `/inventory/raw-material/{rawMaterialInventoryItemId}` | `getRawMaterialInventoryItem` |
| `GET`  | `/raw-material/{rawMaterialId}/inventory` | `listRawMaterialInventoryItemsByRawMaterial` |
| `POST` | `/raw-material/{rawMaterialId}/inventory/_adjust` | `adjustRawMaterialInventory` |

#### `groupedRawMaterialInventoryItemSummary`
```ts
interface groupedRawMaterialInventoryItemSummary {
  raw_material_id: string;
  external_id: string;
  name: string;
  categories: string[];
  uom: string;
  minimum_quantity: number;
  supplier_name: string;
  buckets: { in_stock?: number; in_use?: number; inbound?: number };
  prod_id?: string;
  warehouse_attr?: WarehouseAttr;
  warehouse_id?: string;
}
```

#### `rawMaterialInventoryItemSummary`
```ts
interface rawMaterialInventoryItemSummary {
  id?: string;
  raw_material_id: string;
  external_id: string;
  name: string;
  lot?: string;
  external_lot?: string;
  order_id?: string;
  order?: orderSummary;
  buckets?: rawMaterialInventoryBuckets;
}
```

#### `rawMaterialInventoryAdjustment`
```ts
interface rawMaterialInventoryAdjustment {
  quantity: number;
  reason: string;
  warehouse_id: string;
  warehouse_attr: WarehouseAttr;
  bucket?: string;
}
```

---

### Transport Documents

| Method | Path | Operation |
|--------|------|-----------|
| `POST` | `/transport-document/{transportDocumentId}/_accept` | `acceptTransportDocument` |

#### `transportDocumentDetails` (extends transportDocumentSummary + audit)
```ts
{
  supplier_id?: string;
  weight?: number;
  order?: orderDetails;
  raw_materials: (OrderLineItem & {
    components?: { extra_id: string; id?: string; item_id?: string; lot?: string; name: string; quantity: number; uom: string }[]
  })[];
}
```

---

## Order Status Workflows

**Sales orders:** `draft` → `accepted` → `sent`

**Purchase orders:** `draft` → `sent` → `accepted` → `shipped` (or `rejected`)
