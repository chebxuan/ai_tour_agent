"""Money and scope regression checks; no network, business writes or external LLM."""
from copy import deepcopy
from decimal import Decimal
import unittest
from unittest.mock import patch
import os
from fastapi.testclient import TestClient
from backend.app.services import travel_catalog
from backend.app.engines.cost_engine import load_cost_db


class SalesPricingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {'API_KEY': 'sales-test-only'}):
            from backend.app import main
        cls.client = TestClient(main.app)
        cls.headers = {'X-API-Key': main.API_KEY}

    def post(self, path, payload):
        return self.client.post('/api/v3/' + path, headers=self.headers, json=payload)

    def test_beijing_names_and_optional_increment(self):
        expected = {2: 1144, 3: 1262, 4: 1262}
        for days, total in expected.items():
            response = self.post('internal/cost-estimate', {'city':'北京', 'days':days, 'is_peak':True})
            self.assertEqual(response.status_code, 200)
            cost = response.json()['cost']
            self.assertEqual(cost['summary']['grand_total'], total)
            self.assertNotIn('梨园京剧', [line['name'] for line in cost['line_items']])
            self.assertNotIn('汉服体验', [line['name'] for line in cost['line_items']])
        base={'city':'北京','days':4,'is_peak':True}
        selected=self.post('internal/cost-estimate',{**base,'selected_optional_items':['梨园京剧','汉服体验']})
        self.assertEqual(selected.status_code,200)
        self.assertEqual(selected.json()['cost']['summary']['grand_total'],3062)

    def test_mutually_exclusive_route_cost_and_transport(self):
        for city,days,day,options in [
            ('重庆',2,2,{'wulong':(600,'CQ-TICKET-03','CQ-TICKET-02'),'dazu':(550,'CQ-TICKET-02','CQ-TICKET-03')}),
            ('阳朔',3,3,{'cave':(2380,'YS-ACTIVITY-05','YS-ACTIVITY-09'),'via_ferrata':(2380,'YS-ACTIVITY-09','YS-ACTIVITY-05')}),
            ('张家界',3,3,{'heritage':(1226,'ZJJ-TICKET-07','ZJJ-ACTIVITY-01'),'adventure':(1890,'ZJJ-ACTIVITY-01','ZJJ-TICKET-07')}),
        ]:
            for choice,(total,present,absent) in options.items():
                payload={'city':city,'days':days,'is_peak':False,'route_choices':[{'day':day,'choice':choice}]}
                response=self.post('internal/cost-estimate',payload)
                self.assertEqual(response.status_code,200)
                cost=response.json()['cost'];self.assertEqual(cost['summary']['grand_total'],total)
                self.assertIn(present,cost['regular_item_codes']);self.assertNotIn(absent,cost['regular_item_codes'])
                quote=self.post('trips/quote',payload)
                self.assertEqual(quote.status_code,200)
                self.assertEqual(Decimal(str(quote.json()['sales_quote']['amount'])),Decimal(str(total))*Decimal('1.3'))
        response=self.post('internal/cost-estimate',{'city':'重庆','days':2,'is_peak':False,'need_private_car':True,'route_choices':[{'day':2,'choice':'wulong'}]})
        cost=response.json()['cost'];self.assertEqual(cost['category_subtotals']['transport'],1800)
        transport=[l for l in cost['line_items'] if l['category']=='transport']
        self.assertEqual([(l['code'],l['quantity']) for l in transport],[('CQ-TRANS-01',1),('CQ-TRANS-05',1)])
        response=self.post('internal/cost-estimate',{'city':'张家界','days':3,'is_peak':False,'need_private_car':True,'route_choices':[{'day':3,'choice':'heritage'}]})
        self.assertEqual(response.json()['cost']['category_subtotals']['transport'],2000)

    def test_cruise_once_and_land_services_only(self):
        payload={'city':'重庆','days':5,'is_peak':False,'need_private_car':True,'need_guide':True,'guide_code':'CQ-GUIDE-01'}
        response=self.post('internal/cost-estimate',payload);self.assertEqual(response.status_code,200)
        cost=response.json()['cost'];lines=cost['line_items']
        cruises=[l for l in lines if l['name']=='三峡游轮']
        self.assertEqual(len(cruises),1);self.assertEqual(cruises[0]['code'],'CQ-ACTIVITY-02')
        self.assertEqual(cruises[0]['quantity'],2);self.assertEqual(cruises[0]['subtotal'],4320)
        self.assertEqual(cost['category_subtotals']['guide'],1200)
        self.assertEqual(cost['category_subtotals']['transport'],1200)
        self.assertEqual(cost['summary']['grand_total'],7373)
        self.assertFalse(any(l['code'] in ['CQ-TRANS-09','CQ-TRANS-10','CQ-TICKET-04'] for l in lines))
        quote=self.post('trips/quote',payload).json()['sales_quote']
        self.assertEqual(quote['amount'],9584.90)
        self.assertIn('Yichang-to-Chongqing return train',quote['excluded'])

    def test_quote_whitelist_pending_and_rounding(self):
        # Half-cent values must round upward; 1.3 is a markup, never a 30% margin.
        payload={'city':'重庆','days':5,'adults':3,'is_peak':False}
        quote=self.post('trips/quote',payload)
        self.assertEqual(quote.status_code,200)
        self.assertEqual(quote.json()['sales_quote']['amount'],9697.35)
        with patch('backend.app.services.sales_pricing.travel_catalog.estimate', return_value={'cost': {'summary': {'grand_total': 0.05}}}):
            rounded = self.post('trips/quote', {'city': '北京', 'days': 2, 'is_peak': False})
            self.assertEqual(rounded.json()['sales_quote']['amount'], 0.07)
        forbidden=['unit_price','grand_total','cost','line_items','multiplier','supplier','guide_code','metadata','price_peak']
        for key in forbidden:self.assertNotIn('"'+key+'"',quote.text)
        for city,days in [('重庆',2),('阳朔',3),('张家界',3)]:
            pending=self.post('trips/quote',{'city':city,'days':days,'is_peak':True})
            self.assertEqual(pending.status_code,200)
            self.assertEqual(pending.json()['sales_quote']['status'],'pending_confirmation')
            self.assertIsNone(pending.json()['sales_quote']['amount'])
        for extra in [{'multiplier':9},{'route_choices':[{'day':2,'choice':'wulong'},{'day':2,'choice':'dazu'}]}, {'route_choices':[{'day':1,'choice':'wulong'}]}]:
            self.assertEqual(self.post('trips/quote',{'city':'重庆','days':2,'is_peak':False,**extra}).status_code,422)
        self.assertEqual(self.post('trips/quote',{'city':'重庆','days':2,'is_peak':False,'route_choices':[{'day':2,'choice':'dazu'}],'selected_optional_items':['两江夜游']}).status_code,422)

    def test_all_products_and_quote_auth(self):
        defaults={'CQ-P-01':(2,'wulong'), 'YS-P-02':(3,'cave'), 'ZJJ-P-02':(3,'adventure')}
        for product in travel_catalog.source_products():
            route=defaults.get(product['product_id'])
            payload={'city':product['city'],'days':product['duration_days'],'is_peak':False,
                     'route_choices':[{'day':route[0],'choice':route[1]}] if route else []}
            response=self.post('trips/quote',payload)
            self.assertEqual(response.status_code,200,product['product_id'])
            if product['product_id'] == 'GZ-P-01':
                self.assertEqual(response.json()['sales_quote']['reason'], 'NO_PRICED_SERVICES')
                self.assertIsNone(response.json()['sales_quote']['amount'])
            else:
                self.assertEqual(response.json()['sales_quote']['status'],'estimated',product['product_id'])
                self.assertGreater(response.json()['sales_quote']['amount'],0)
        self.assertEqual(self.client.post('/api/v3/trips/quote',headers={'X-API-Key':'wrong'},json={'city':'上海','days':3,'is_peak':False}).status_code,401)
        self.assertEqual(self.post('trips/quote',{'city':'上海','days':3,'is_peak':False,'need_guide':True}).status_code,422)

    def test_public_quote_choices_match_menu(self):
        response = self.client.get('/api/v3/products', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        products = response.json()['products']
        for product in products:
            self.assertTrue(product['quote_guide_options'])
            for guide in product['quote_guide_options']:
                self.assertEqual(set(guide), {'code', 'label'})
                self.assertIn(guide['label'], ['English-speaking guide', 'Senior English-speaking guide'])
            for route in product['quote_route_options']:
                menu_day = product['menu']['days'][route['day'] - 1]
                self.assertIn(route['choice'], [branch['choice'] for branch in menu_day['alternatives']])
                self.assertTrue(set(route['excluded_optional_items']).issubset({item['name'] for item in product['optional_choices']}))
        quoted = self.post('trips/quote', {'city':'上海','days':3,'is_peak':False,'selected_optional_items':['黄浦江夜游']})
        self.assertIn('Selected experience: Huangpu River Night Cruise', quoted.json()['sales_quote']['included'])
        specialised = self.post('trips/quote', {'city':'西安','days':3,'is_peak':False,'need_guide':True,'guide_code':'XA-GUIDE-02'})
        self.assertEqual(specialised.json()['sales_quote']['reason'], 'GUIDE_SCOPE_REQUIRES_REVIEW')
        self.assertIsNone(specialised.json()['sales_quote']['amount'])

    def test_conflict_cannot_fall_back_to_old_total(self):
        original=load_cost_db(city='北京');bad=deepcopy(original);bad['BJ-TICKET-05']['name']='梨园京剧'
        with patch('backend.app.services.cost_scope.load_cost_db',return_value=bad):
            internal=self.post('internal/cost-estimate',{'city':'北京','days':2,'is_peak':True})
            self.assertEqual(internal.status_code,409);self.assertNotIn('grand_total',internal.text)
            public=self.post('trips/quote',{'city':'北京','days':2,'is_peak':True})
            self.assertIsNone(public.json()['sales_quote']['amount'])
            self.assertEqual(public.json()['sales_quote']['status'],'pending_confirmation')
        bad=deepcopy(original);bad['BJ-TICKET-05']['price']=0
        with patch('backend.app.services.cost_scope.load_cost_db',return_value=bad):
            self.assertEqual(self.post('internal/cost-estimate',{'city':'北京','days':2,'is_peak':False}).status_code,409)
        bad = deepcopy(original); bad['BJ-GUIDE-01']['price'] = 0; bad['BJ-GUIDE-01']['price_peak'] = 0
        with patch('backend.app.services.travel_catalog.load_cost_db', return_value=bad):
            response = self.post('trips/quote', {'city':'北京','days':2,'is_peak':False,'need_guide':True,'guide_code':'BJ-GUIDE-01'})
            self.assertEqual(response.json()['sales_quote']['reason'], 'GUIDE_COST_REQUIRES_REVIEW')
            self.assertIsNone(response.json()['sales_quote']['amount'])


if __name__=='__main__':unittest.main()
