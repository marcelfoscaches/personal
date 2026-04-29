public class Cliente {
  public long Cnpj { get; set; }
  public string Validar(string cnpj){
    var digits = Regex.Replace(cnpj, @"\D", "");
    if(digits.Length == 14 && Regex.IsMatch(digits, @"^\d+$")) return "ok";
    return "CNPJ aceita somente numeros";
  }
}
