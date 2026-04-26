import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';

export const concerts = sqliteTable('concerts', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  sn: text('sn').unique().notNull(),
  title: text('title').notNull(),
  titleEng: text('title_eng'),
  beginDate: text('begin_date').notNull(),
  endDate: text('end_date'),
  playtime: text('playtime'),
  placeName: text('place_name'),
  placeCode: text('place_code'),
  priceInfo: text('price_info'),
  saleState: text('sale_state'),
  detailText: text('detail_text'),
  startWeek: text('start_week'),
  sacUrl: text('sac_url'),
  crawledAt: text('crawled_at').notNull(),
});
