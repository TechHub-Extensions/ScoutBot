import scrapy


class OpportunityItem(scrapy.Item):
    title = scrapy.Field()
    industry = scrapy.Field()
    category = scrapy.Field()
    range = scrapy.Field()
    education_level = scrapy.Field()
    organization = scrapy.Field()
    summary = scrapy.Field()
    application_link = scrapy.Field()
    opening_date = scrapy.Field()
    deadline = scrapy.Field()
    status = scrapy.Field()
