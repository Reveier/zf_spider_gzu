# -*- coding: utf-8 -*-
import csv
import ddddocr
import re
import requests
import bs4
from prettytable import PrettyTable
from PIL import Image
import os
import sys

sys.setrecursionlimit(10000)


class Spider:

    def __init__(self):
        self.__base_url = 'https://jw.gzu.edu.cn/'
        self.__uid = ''
        self.__name = ''
        self.__LOGIN_VIEWSTATE = ''
        self.__header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/103.0.5060.53 Safari/537.36 Edg/103.0.1264.37 ',
        }
        self.__is_login = False
        self.session = requests.Session()

    def __get_code(self):
        pic = self.session.get(self.__base_url + 'CheckCode.aspx', headers=self.__header)
        with open('ver_pic.png', 'wb') as f:
            f.write(pic.content)
        # 打开验证码图片
        # image = Image.open('{}/ver_pic.png'.format(os.getcwd()))
        # image.show()
        # print('Please input the code:')
        # code = input()
        # 识别验证码
        ocr = ddddocr.DdddOcr()
        with open('ver_pic.png', 'rb') as f:
            image_bytes = f.read()
        code = ocr.classification(image_bytes)
        return code

    def __get_login_data(self, uid, password):
        self.__uid = uid
        # 获取登录的VIEWSTATE
        res = self.session.get(self.__base_url, headers=self.__header)
        soup = bs4.BeautifulSoup(res.text, 'html.parser')
        __VIEWSTATE = soup.find('input', attrs={'name': '__VIEWSTATE'})['value']
        self.__LOGIN_VIEWSTATE = __VIEWSTATE
        # 获取验证码
        code = self.__get_code()
        data = {
            '__VIEWSTATE': __VIEWSTATE,
            'txtUserName': self.__uid,
            'TextBox2': password,
            'txtSecretCode': code,
            'RadioButtonList1': '学生'.encode('gb2312'),
            'Button1': '',
            'lbLanguage': '',
            'hidPdrs': '',
            'hidsc': '',
        }
        return data

    def __login(self, uid, password):
        data = self.__get_login_data(uid, password)
        res = self.session.post(self.__base_url + 'default2.aspx', headers=self.__header, data=data)
        soup = bs4.BeautifulSoup(res.text, 'html.parser')
        try:
            name_tag = soup.find(id='xhxm')
            self.__name = name_tag.string[:len(name_tag.string) - 2]
            print('欢迎' + self.__name)
            self.__is_login = True
        except:
            print('Unknown Error,try to login again.')
            self.__is_login = False
            return False

    def get_all_score(self):
        score_url = self.__base_url + 'xscj_gc.aspx?xh={}&xm={}&gnmkdm=N121605'.format(self.__uid, self.__name)
        # 获取content里面的VIEWSTATE
        referer = 'https://jw.gzu.edu.cn/xs_main.aspx?xh={}'.format(self.__uid)
        self.__header['Referer'] = referer
        content = self.session.get(score_url, headers=self.__header)
        content_soup = bs4.BeautifulSoup(content.text, 'html.parser')
        __VIEWSTATE = re.findall('<input name="__VIEWSTATE" type="hidden" value="(.+?)"', str(content_soup))[0]

        # post数据
        data = {
            '__VIEWSTATE': __VIEWSTATE,
            'ddlXN': '',
            'ddlXQ': '',
            'Button1': '按学期查询'.encode('gb2312')
        }
        referer = 'https://jw.gzu.edu.cn/xscj_gc.aspx?xh={}&xm={}&gnmkdm=N121605'.format(self.__uid,
                                                                                         self.__name).encode('gb2312')
        self.__header['Referer'] = referer
        # self.__header['Origin'] = 'https://jw.gzu.edu.cn'
        # 获取成绩请求
        res = self.session.post(score_url, headers=self.__header, data=data)
        soup = bs4.BeautifulSoup(res.text, 'html.parser')
        score_table_tr = soup.find(class_='datelist').find_all('tr')
        # 成绩信息存储为csv
        with open("save_{}_scores.csv".format(self.__uid), 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            score_list = []
            for i in range(len(score_table_tr)):
                row_list = []
                if i == 0:
                    col_list = []
                    tds = score_table_tr[0].find_all('td')
                    for td in tds:
                        col_list.append(str(td.string).strip())
                    writer.writerow(col_list)
                else:
                    tds = score_table_tr[i].find_all('td')
                    for td in tds:
                        row_list.append(str(td.string).strip())
                    score_list.append(row_list)
            writer.writerows(score_list)
        print('成绩已存储为csv文件！')

    def get_all_course(self):
        course_url = self.__base_url + 'xskbcx.aspx?xh={}&xm={}&gnmkdm=N121603'.format(self.__uid, self.__name)
        referer = 'https://jw.gzu.edu.cn/xs_main.aspx?xh={}'.format(self.__uid)
        self.__header['Referer'] = referer
        res = self.session.get(course_url, headers=self.__header)
        soup = bs4.BeautifulSoup(res.text, 'html.parser')
        table = soup.find(class_='blacktab')
        # 忽略第一行时间 与 第二行早晨
        trs = table.find_all('tr')
        course_list = []
        for i in range(2, len(trs)):
            tds = trs[i].find_all('td')
            for j in range(2, len(tds)):
                li = list(tds[j].strings)
                if len(li) == 1:
                    continue
                for k in range(0, len(li), 4):
                    if k + 4 > len(li):
                        break
                    one_course_list = [li[k], li[k + 1], li[k + 2], li[k + 3]]
                    course_list.append(one_course_list)
        course_table = PrettyTable(['课程名称', '时间', '任课老师', '地点'])
        course_table.add_rows(course_list)
        course_table.align['课程名称'] = 'l'
        course_table.align['时间'] = 'r'
        course_table.align['地点'] = 'r'
        print(course_table)

    def run(self, uid, password):
        if self.__login(uid, password) is False:
            return
        while True:
            if self.__is_login is not True:
                print('ERROR!')
                return
            print('----- 1->查询所有成绩 -----')
            print('----- 2->查询课表 -----')
            print('----- 0->退出 -----')
            choice = input('请选择操作：')
            if int(choice) == 1:
                self.get_all_score()
            elif int(choice) == 2:
                self.get_all_course()
            elif int(choice) == 0:
                print("退出！！！")
                return


if __name__ == '__main__':
    jw = Spider()
    jw.run('学号', '密码')
