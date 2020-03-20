import re
import binascii
from urllib.parse import unquote
from win32api import GetSystemMetrics
from requests_html import HTMLSession, AsyncHTMLSession

class LandChinaBot:
	info_all = []
	url = 'https://www.landchina.com/'
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
		# 'Cookie': 'security_session_mid_verify=b92679e3c892fc921cb78030f1e86157',
	}
	data = None

	def __init__(self, city_code, city_name):
		self.getCityInfo(city_code, city_name)
		self.async_session = AsyncHTMLSession()

	def getCityInfo(self, city_code, city_name):
		city_info = unquote(f'42ad98ae-c46a-40aa-aacc-c0884036eeaf:{city_code}' + u"▓~" + city_name)
		city_info = city_info.encode("gb18030")
		self.data = {
			'TAB_QuerySubmitConditionData': city_info,
		}

	@staticmethod
	def stringToHex():
		width = str(GetSystemMetrics(0));
		height = str(GetSystemMetrics(1));
		screendate = width + "," + height;
		val = ""
		for i in range(len(screendate)):
			if val == "":
				val = binascii.b2a_hex(screendate[i].encode('utf-8'))
			else:
				pass
				val += binascii.b2a_hex(screendate[i].encode('utf-8'))
		return val.decode('utf-8')

	async def getCookie(self):
		response = await self.async_session.get(self.url, headers = self.headers)
		security_verify_data = self.stringToHex()
		link = f'{self.url}?security_verify_data={security_verify_data}'
		response = await self.async_session.get(link, headers = self.headers)
		# print(self.async_session.cookies)

	async def getInfo(self, session):
		# detail_link = []
		link = f'{self.url}default.aspx?tabid=263'
		response = await session.post(link, data = self.data, headers = self.headers)
		# print(response.text)
		info = response.html.xpath('//*[@id="TAB_contentTable"]/tbody/tr')
		for sub_raw in info[1:]:
			info_basic = {}
			basic_value = []
			sub_list = sub_raw.xpath('//td')
			for i, info_sub in enumerate(sub_list):
				if i != 2:
					info_sub =  info_sub.xpath('//text()')[0]
					# print(info_sub, end=' ')
					basic_value.append(info_sub)
				else:
					link_sub = info_sub.xpath('//a/@href')[0]
					# detail_link.append(link_sub)
					try:
						info_sub = info_sub.xpath('//a/text()')[0]
					except IndexError:
						info_sub = info_sub.xpath('//a/span/@title')[0]
					# print(info_sub, end=' ')
					basic_value.append(info_sub)
			# print('\n')
			details = await self.getDetail(link_sub, self.async_session)
			info_basic['序号'] = basic_value[0][:-1]
			info_basic['行政区'] = basic_value[1]
			info_basic['土地坐落'] = basic_value[2]
			info_basic['总面积'] = basic_value[3]
			info_basic['土地用途'] = basic_value[4]
			info_basic['供应方式'] = basic_value[5]
			info_basic['签订日期'] = basic_value[6]
			info_basic['供地结果信息'] = details
			self.info_all.append(info_basic)
		# return detail_link

	async def getDetail(self, link, session):
		link = f'{self.url}{link}'
		# print(link)
		response = await session.get(link, headers = self.headers)
		# print(response.text)
		info = response.html.xpath('//*[contains(@id, "mainModuleContainer_1855_1856_ctl00_ctl00_p1_")]/text()')
		# print(info)
		if not info:
			return False
		info_new = ''
		pay_i = right_i = None
		# 计算出'土地来源'对应的实际数据
		# 去除空值，并将数据变换为键值对形式，并以#分隔
		for i, info_sub in enumerate(info):
			if '土地来源' in info_sub:
				if float(info[i+1]) == float(info[i-1]):
					info[i+1] = '现有建设用地'
				elif float(info[i+1]) == 0:
					info[i+1] = '新增建设用地'
				else:
					info[i+1] = '新增建设用地(来自存量库)'
			elif '分期支付约定' in info_sub:
				pay_i = i
			elif '土地使用权人' in info_sub:
				right_i = i
			if info_sub != '\xa0':
				info_sub  = f'"{info_sub}"'
				if '：' in info_sub or ':' in info_sub:
					info_sub  = f'#{info_sub[:-2]}":'
				# 获取'分期支付约定'对应的实际数据
				if pay_i == i:
					info_sub  = info_sub + '['
				if not right_i and pay_i and i > pay_i:
					info_sub  = info_sub + ','
				if right_i == i:
					info_sub  = ']' + info_sub
				info_new += info_sub
		#
		info_new = info_new.split('#')
		# 获取'约定容积率'对应的实际数据
		volume_i = info_new.index('"约定容积率":')
		if info_new[volume_i+1][-1] == ':':
			info_new[volume_i+1] += '""'
		info_new[volume_i+1] = '{' + info_new[volume_i+1] + ','
		if info_new[volume_i+2][-1] == ':':
			info_new[volume_i+2] += '""'
		info_new[volume_i+2] = info_new[volume_i+2] + '}'
		info_new[volume_i] = f'{info_new[volume_i]}{info_new[volume_i+1]}{info_new[volume_i+2]}'
		info_new.pop(volume_i+1)
		info_new.pop(volume_i+1)
		# 补充空值，构成字典
		info = '{'
		for i, info_sub in enumerate(info_new[1:]):
			if len(info_sub) > 1 and info_sub[-1] == ':':
				info_sub += '""'
			info += f'{info_sub},'
		info += '}'
		info = eval(info)
		# 获取'分期支付约定'对应的实际数据
		pay_info = info['分期支付约定'][4:]
		if pay_info:
			pay_info_new = '['
			for i, info_sub in enumerate(pay_info):
				info_sub = f"'{info_sub}',"
				if re.match(r"^\'\d+\',$", info_sub):
					info_sub = '[' + info_sub
					if i > 1 :
						pay_info_new =pay_info_new[:-1] + "],"
				pay_info_new += info_sub
			pay_info_new =pay_info_new[:-1] + "]]"
			pay_info_new = eval(pay_info_new)
			# 去重
			info_index = None
			pay_info = []
			for info_sub in pay_info_new:
				if info_index != info_sub[0]:
					# 补充相关
					info_pay = {}
					for i in range(4-len(info_sub)):
						info_sub.append('')
					info_pay['支付期号'] = info_sub[0]
					info_pay['约定支付日期'] = info_sub[1]
					info_pay['约定支付金额(万元)'] = info_sub[2]
					info_pay['备注'] = info_sub[3]
					pay_info.append(info_pay)
					info_index = info_sub[0]
			info['分期支付约定'] = pay_info
		else:
			info['分期支付约定'] = []
		# print(info, '\n\n')
		return info

	async def run(self):
		await self.getCookie()
		await self.getInfo(self.async_session)
		for info_sub in self.info_all:
			print(info_sub, '\n\n')

	def main(self):
		self.async_session.run(self.run)

if __name__ == '__main__':
	bot = LandChinaBot('31', '上海市')
	bot.main()