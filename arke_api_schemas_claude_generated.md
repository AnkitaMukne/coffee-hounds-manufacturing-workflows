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

## Production API


| Operation ID | Method | Path | Namespace |
|---|---|---|---|
| `listProducts` | GET | `/product` | product-api |
| `createProduct` | PUT | `/product` | product-api |
| `showProduct` | GET | `/product/{productId}` | product-api |
| `archiveProduct` | DELETE | `/product/{productId}` | product-api |
| `lookupProduct` | GET | `/product/_lookup` | product-api |
| `extractProduct` | POST | `/product/_extract` | product-api |
| `listCategories` | GET | `/product/_categories` | product-api |
| `listProductSuppliers` | GET | `/product/{productId}/supplier` | product-api |
| `createProductSupplier` | PUT | `/product/{productId}/supplier` | product-api |
| `showProductSupplier` | GET | `/product/{productId}/supplier/{supplierId}` | product-api |
| `listProductInventoryItemByProduct` | GET | `/product/{productId}/inventory` | product-api |
| `listProductInventoryItems` | GET | `/inventory/product` | product-api |
| `showProductInventoryItem` | GET | `/inventory/product/{productInventoryItemId}` | product-api |
| `showMasterProduct` | GET | `/master-product/{masterProductId}` | product-api |
| `getProductPriceDetails` | GET | `/customer/{customerId}/products/{productId}/_computed-price-details` | sales-api |
| `getCustomerPriceList` | GET | `/customer/{customerId}/offer/_price-list` | sales-api |
| `createProductionOrder` | PUT | `/production` | product-api |
| `showProduction` | GET | `/production/{productionOrderId}` | product-api |
| `scheduleProduction` | POST | `/production/{productionOrderId}/_schedule` | product-api |
| `startProduction` | POST | `/production/{productionOrderId}/_start` | product-api |
| `completeProduction` | POST | `/production/{productionOrderId}/_complete` | product-api |
| `lastTwoMonthProduction` | GET | `/production/_last_two_month_production` | product-api |
| `createProductionPlan` | PUT | `/production-plan` | product-api |
| `listProductionPhases` | GET | `/production-phase` | product-api |
| `createProductionPhase` | PUT | `/production-phase` | product-api |
| `listOrderPhases` | GET | `/production-phase/{phaseId}/order-phase` | product-api |
| `showProductionOrderPhase` | GET | `/production-order-phase/{orderPhaseId}` | product-api |
| `startProductionPhase` | POST | `/production-order-phase/{orderPhaseId}/_start` | product-api |
| `completeProductionPhase` | POST | `/production-order-phase/{orderPhaseId}/_complete` | product-api |
| `listProductionOrderPhaseNotes` | GET | `/production-order-phase/{orderPhaseId}/notes` | product-api |
| `calculateSupplyNeedsForProduction` | POST | `/analytics/supply-needs/_calculate-for-production` | supply-api |

---

## Product Routes (product-api)

### GET /product — `listProducts`
**Response 200:** `productSummary[]`

### PUT /product — `createProduct`
**Request body:** `productDetails`
**Response 201:** `productDetails`

### GET /product/{productId} — `showProduct`
**Response 200:** `productDetails`

### DELETE /product/{productId} — `archiveProduct`
No response body.

### GET /product/_lookup — `lookupProduct`
**Response 200:** `productDetails`

### GET /product/_categories — `listCategories`
**Response 200:** (no typed schema)

### POST /product/_extract — `extractProduct`
**Request body:** `upload`
**Response 200:** `bomExDocument[]`

### GET /product/{productId}/supplier — `listProductSuppliers`
**Response 200:** `productSupplierSummary[]`

### PUT /product/{productId}/supplier — `createProductSupplier`
**Request body:** `productSupplierDetails`
**Response 200:** `productSupplierDetails`

### GET /product/{productId}/supplier/{supplierId} — `showProductSupplier`
**Response 200:** `productSupplierDetails`

### GET /product/{productId}/inventory — `listProductInventoryItemByProduct`
**Response 200:** `productInventoryItemSummary[]`

### GET /inventory/product — `listProductInventoryItems`
**Response 200:** `productInventoryItemSummary[]`

### GET /inventory/product/{productInventoryItemId} — `showProductInventoryItem`
**Response 200:** `productInventoryItemDetails`

### GET /master-product/{masterProductId} — `showMasterProduct`
**Response 200:** `masterProductDetails`

---

## Production Routes (product-api)

### PUT /production — `createProductionOrder`
**Request body:** `createProductionOrderRequest`
**Response 201:** `productionOrder`

### GET /production/{productionOrderId} — `showProduction`
**Response 200:** `productionOrder`

### POST /production/{productionOrderId}/_schedule — `scheduleProduction`
**Response 200:** `productionOrder`

### POST /production/{productionOrderId}/_start — `startProduction`
**Response 200:** `productionOrder`

### POST /production/{productionOrderId}/_complete — `completeProduction`
**Response 200:** `productionOrder`

### GET /production/_last_two_month_production — `lastTwoMonthProduction`
**Response 200:** `monthlyProduction[]`

### PUT /production-plan — `createProductionPlan`
**Request body:** `productionPlanCreate`
**Response 201:** `productionPlan`

### GET /production-phase — `listProductionPhases`
**Response 200:** `productionPhaseSummary[]`

### PUT /production-phase — `createProductionPhase`
**Request body:** `productionPhaseDetails`
**Response 201:** `productionPhaseDetails`

### GET /production-phase/{phaseId}/order-phase — `listOrderPhases`
**Response 200:** `productionOrderPhaseSummary[]`

### GET /production-order-phase/{orderPhaseId} — `showProductionOrderPhase`
**Response 200:** `productionOrderPhaseDetails`

### POST /production-order-phase/{orderPhaseId}/_start — `startProductionPhase`
**Response 200:** `productionOrderPhaseDetails`

### POST /production-order-phase/{orderPhaseId}/_complete — `completeProductionPhase`
**Request body:** `orderPhaseCompletionRequest`
**Response 200:** `productionOrderPhaseDetails`

### GET /production-order-phase/{orderPhaseId}/notes — `listProductionOrderPhaseNotes`
**Response 200:** `productionOrderPhaseNote[]`

---

## Analytics Routes (supply-api)

### POST /analytics/supply-needs/_calculate-for-production — `calculateSupplyNeedsForProduction`
**Request body:** `supplyNeedsDetails`
**Response 200:** `missingRawMaterial[]`

---

## Sales Routes (sales-api)

### GET /customer/{customerId}/products/{productId}/_computed-price-details — `getProductPriceDetails`
**Response 200:** `productPriceDetails`

### GET /customer/{customerId}/offer/_price-list — `getCustomerPriceList`
**Response 200:** (no typed schema)

---

## Type Schemas

### `productSummary`
```typescript
interface productSummary {
  id?: string;           // uuid
  uom: string;
  name: string;
  type: "producible" | "purchasable" | "bundle";
  prices: priceInfo;
  created?: auditInfo;
  semi_id?: string;      // uuid
  categories: string[];
  internal_id?: string;
  master_product?: masterProductSummary;
  master_product_id?: string; // uuid
}
```

### `productDetails`
```typescript
type productDetails = baseDocument & productSummary & {
  archived?: boolean;
  notes?: string;
  version: number;
  foreign_ids?: Record<string, unknown>;
  custom_form_values?: customFormValues;
  created?: auditEntry;
  updated?: auditEntry;
  attributes?: Record<string, unknown>;
  bundled_products?: materialItem[];
  description: string;
  plan?: planPhase[];
  process_lines?: processLine[];
  raw_materials?: materialItem[];
  track_supplier_warehouses?: boolean;
  variant_selections?: variantSelection[];
}
```

### `masterProductSummary`
```typescript
interface masterProductSummary {
  id?: string;           // uuid
  uom: string;
  name: string;
  type: "producible" | "purchasable" | "bundle";
  created?: auditInfo;
  categories: string[];
  description?: string;
  internal_id?: string;
  variant_axes?: variantAxis[];
  variant_count?: number;
}
```

### `masterProductDetails`
```typescript
type masterProductDetails = baseDocument & masterProductSummary & {
  attributes?: Record<string, unknown>;
  plan?: planPhase[];
  process_lines?: processLine[];
  variant_axes?: variantAxis[];
  variants?: variantSummary[];
}
```

### `productSupplierSummary`
```typescript
interface productSupplierSummary {
  id?: string;             // uuid
  uom?: string;
  name?: string;
  prices?: priceInfo;
  created?: auditInfo;
  categories?: string[];
  description?: string;
  external_id: string;
  supplier_id: string;     // uuid
  supplier_attr?: companySnapshot;
  aggregate_of_id?: string;
  aggregate_quantity?: number;
}
```

### `productSupplierDetails`
```typescript
type productSupplierDetails = baseDocument & productSupplierSummary & {
  aggregate_of_id?: string;
  aggregate_quantity?: number;
  attributes?: Record<string, unknown>;
  lead_time?: string;
  minimum_quantity: number;
}
```

### `productInventoryItemSummary`
```typescript
interface productInventoryItemSummary {
  id?: string;
  lot?: string;
  uom: string;
  name: string;
  buckets?: productBuckets;
  created?: auditInfo;
  semi_id?: string;           // uuid
  order_id?: string;          // uuid
  categories: string[];
  product_id: string;
  internal_id: string;
  external_lot?: string;
  warehouse_id?: string;      // uuid
  warehouse_attr?: Record<string, unknown>;
  order_external_id?: string;
  order_internal_id?: string;
}
```

### `productInventoryItemDetails`
```typescript
type productInventoryItemDetails = baseDocument & productInventoryItemSummary & {
  raw_materials?: {
    external_lot?: string;
    extra_id: string;
    id?: string;
    item_id?: string;
    lot?: string;
    meta?: Record<string, unknown>;
    name: string;
    order_id?: string;
    prices?: priceInfo;
    quantity: number;
    uom: string;
  }[];
}
```

### `productBuckets`
```typescript
interface productBuckets {
  planned: number;
  in_production: number;
  available: number;
  reserved: number;
  shipped: number;
}
```

### `productPriceDetails`
```typescript
interface productPriceDetails {
  affiliate_customer_id?: string;
  applied_offer_id?: string;
  applied_price: priceInfo;
  applied_source: "catalog" | "customer" | "offer";
  best_offer?: offerPriceDetail;
  catalog_price: priceInfo;
  customer_price?: priceInfo;
  offer_prices?: offerPriceDetail[];
  product_id: string;
  product_internal_id?: string;
  product_name: string;
}
```

### `createProductionOrderRequest`
```typescript
interface createProductionOrderRequest {
  product_id: string;      // uuid (required)
  starts_at: string;       // date-time (required)
  ends_at: string;         // date-time (required)
  quantity: number;        // float (required)
  production_plan_id?: string; // uuid
  custom_form_values?: customFormValues;
}
```

### `productionOrder`
```typescript
type productionOrder = baseDocument & {
  id: string;
  duration: number;
  ended_at?: string;
  ends_at: string;
  logs: productionOrderLog[];
  lot?: string;
  orders?: string[];
  phases?: productionOrderPhaseSummaryBase[];
  plan: planPhase[];
  produced_quantity?: number;
  product_categories: string[];
  product_id: string;
  product_internal_id: string;
  product_name: string;
  product_semi_id?: string;
  production_plan_id?: string;
  quantity: number;
  started_at?: string;
  starts_at: string;
  status: "draft" | "planned" | "scheduled" | "in_progress" | "completed";
  uom: string;
}
```

### `productionOrderLog`
```typescript
interface productionOrderLog {
  id: string;              // uuid
  event: "scheduled" | "started" | "completed" | "updated";
  quantity?: number;
  created_at: string;      // date-time
}
```

### `productionPlanCreate`
```typescript
interface productionPlanCreate {
  name: string;            // required, e.g. "January 2026 Production Schedule"
  starting_date?: string;  // date-time
  ending_date?: string;    // date-time
  custom_form_values?: customFormValues;
}
```

### `productionPlan`
```typescript
type productionPlan = baseDocument & {
  id: string;
  name: string;
  ending_date?: string;
  starting_date?: string;
  status?: "draft" | "active";
  production_orders?: productionOrder[];
}
```

### `productionPhaseSummary`
```typescript
interface productionPhaseSummary {
  id?: string;
  name?: string;
  description?: string;
}
```

### `productionPhaseDetails`
```typescript
type productionPhaseDetails = baseDocument & productionPhaseSummary;
```

### `productionOrderPhaseSummaryBase`
```typescript
interface productionOrderPhaseSummaryBase {
  id: string;              // uuid
  status: "not_ready" | "ready" | "started" | "completed";
  step?: number;
  phase?: productionPhaseSummary;
  logs?: productionOrderPhaseLog[];
  ends_at?: string;
  ended_at?: string;
  starts_at?: string;
  percentage?: number;
  started_at?: string;
}
```

### `productionOrderPhaseSummary`
```typescript
type productionOrderPhaseSummary = productionOrderPhaseSummaryBase & {
  production_order: productionOrder;
}
```

### `productionOrderPhaseDetails`
```typescript
type productionOrderPhaseDetails = baseDocument & productionOrderPhaseSummary & {
  is_final: boolean;
  raw_material_inventory: rawMaterialInventoryItem[];
  raw_materials: materialItem[];
}
```

### `productionOrderPhaseLog`
```typescript
interface productionOrderPhaseLog {
  id: string;              // uuid
  event: "started" | "completed";
  created_at: string;      // date-time
}
```

### `productionOrderPhaseNote`
```typescript
interface productionOrderPhaseNote {
  id?: string;
  text?: string;
  created?: auditEntry;
}
```

### `orderPhaseCompletionRequest`
```typescript
interface orderPhaseCompletionRequest {
  raw_material_inventory: rawMaterialInventoryItem[];  // required
  completed?: number;
  skip_consumption?: boolean;  // if true, skips raw material consumption & inventory feasibility checks
}
```

### `rawMaterialInventoryItem`
```typescript
interface rawMaterialInventoryItem {
  id: string;    // uuid (required)
  uom: string;   // required
  buckets: phaseRawMaterialBuckets;  // required
}
```

### `phaseRawMaterialBuckets`
```typescript
interface phaseRawMaterialBuckets {
  needed: number;    // required
  consumed: number;  // required
  reserved: number;  // required
  scrapped: number;  // required
}
```

### `monthlyProduction`
```typescript
interface monthlyProduction {
  month: string;
  lot_count: number;
}
```

### `supplyNeedsDetails`
```typescript
interface supplyNeedsDetails {
  id: string;        // uuid (required) — production order ID
  quantity: number;  // float (required)
}
```

### `missingRawMaterial`
```typescript
type missingRawMaterial = rawMaterialSummary & {
  alternatives?: missingRawMaterial[];
  estimated_cost?: priceInfo;
  inventory: rawMaterialInventory;
}
```

### `rawMaterialInventory`
```typescript
interface rawMaterialInventory {
  in_use: number;
  needed: number;
  inbound: number;
  missing: number;
  ordered: number;
  in_stock: number;
}
```

### `rawMaterialSummary`
```typescript
interface rawMaterialSummary {
  id?: string;               // uuid
  uom: string;
  name: string;
  prices?: priceInfo;
  created?: auditInfo;
  prod_id?: string;          // uuid
  lead_time?: string;
  categories: string[];
  description?: string;
  external_id: string;
  supplier_id: string;       // uuid
  supplier_attr?: companySnapshot;
  aggregate_of_id?: string;  // uuid
  minimum_quantity: number;
  aggregate_quantity?: number;
  purchasable_product_id?: string; // uuid
}
```

### `upload`
```typescript
interface upload {
  file: string;
  name: string;
  document_type_hint?: string;
}
```

### `bomExDocument`
```typescript
interface bomExDocument {
  apiVersion: "arke.so/api/v1";
  kind: string;
  metadata: {
    annotations?: unknown;
    creationTimestamp?: string;
    uid?: string;
  };
  namespace: string;
  spec: bomExSpec;
}
```

### `bomExSpec`
```typescript
interface bomExSpec {
  name: string;
  attr_color: unknown;
  external_id?: string;
  raw_materials: extractedRawMaterial[];
}
```

### `extractedRawMaterial`
```typescript
interface extractedRawMaterial {
  name: string;
  quantity: number;
  uom?: string;
  code?: string;
  attr_size?: number;
  attr_color?: unknown;
}
```

---

## Shared / Base Types

### `priceInfo`
```typescript
interface priceInfo {
  unit: number;
  currency: "EUR" | "USD" | "GBP";
  base_price?: number;
  discount_percent?: number;
  vat?: number;
  deals?: {
    min_quantity: number;
    unit: number;
    category?: string;
  }[];
}
```

### `auditEntry`
```typescript
interface auditEntry {
  at: string;
  by: {
    id: string;
    username: string;
    full_name: string;
  };
}
```

### `companySnapshot`
```typescript
interface companySnapshot {
  name: string;
  vat: string;
  id?: string;
  address?: string;
  country?: string;
}
```

### `planPhase`
```typescript
interface planPhase {
  operator: "and" | "or" | "xor";
  processes: planProcess[];
}
```

### `planProcess`
```typescript
interface planProcess {
  properties: Record<string, unknown>;
  requirements?: planRequirements;
  custom_form_values?: customFormValues;
}
```

### `processLine`
```typescript
interface processLine {
  name: string;
  station: string;
  duration: string;
  description: string;
}
```

### `variantAxis`
```typescript
interface variantAxis {
  id?: string;    // uuid
  name: string;   // e.g. "Color", "Size", "Material"
  options: variantOption[];
}
```

### `variantOption`
```typescript
interface variantOption {
  id?: string;    // uuid
  value: string;  // e.g. "Blue", "Small", "Cotton"
}
```

### `variantSelection`
```typescript
interface variantSelection {
  axis_id: string;    // uuid
  option_id: string;  // uuid
}
```

### `offerPriceDetail`
```typescript
interface offerPriceDetail {
  offer_id: string;
  offer_name: string;
  price: priceInfo;
  status: "draft" | "sent" | "accepted" | "rejected";
  validity_start: string;  // date-time
  validity_end: string;    // date-time
  offer_internal_id?: string;
}
```

### `materialItem`
```typescript
interface materialItem {
  extra_id: string;
  name: string;
  quantity: number;
  uom: string;
  id?: string;
  item_id?: string;
  lot?: string;
  order_id?: string;
  external_lot?: string;
  components?: {
    extra_id: string;
    name: string;
    quantity: number;
    uom: string;
    id?: string;
    item_id?: string;
    lot?: string;
  }[];
}
```

### `baseDocument`
```typescript
interface baseDocument {
  archived?: boolean;
  version: number;
  notes?: string;
  foreign_ids?: Record<string, unknown>;
  custom_form_values?: customFormValues;
  created?: auditEntry;
  updated?: auditEntry;
}
```

### `customFormValues`
```typescript
interface customFormValues {
  generation?: number;
  values?: ({
    index: number;
    label: string;
    name: string;
    type: string;
    filters?: { name: string; value: string }[];
  } & { value?: unknown })[];
}
```
