# Arke API — Product & Production Routes

## Route Summary

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
