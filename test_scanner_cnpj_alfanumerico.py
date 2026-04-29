import unittest
from scanner_cnpj_alfanumerico import build_rules

class TestRules(unittest.TestCase):
    def setUp(self):
        self.rules = {r.id: r for r in build_rules([])}

    def test_regex_numerico(self):
        line = 'Regex.IsMatch(cnpj, @"^\\d{14}$")'
        self.assertTrue(self.rules['REGEX_CNPJ_NUMERICO'].pattern.search(line))

    def test_somente_digitos(self):
        line = 'digits = Regex.Replace(cnpj, @"\\D", "")'
        self.assertTrue(self.rules['SOMENTE_DIGITOS'].pattern.search(line))

    def test_banco_coluna_numerica(self):
        line = 'cnpj numeric(14,0)'
        self.assertTrue(self.rules['BANCO_COLUNA_NUMERICA'].pattern.search(line))

if __name__ == '__main__':
    unittest.main()
