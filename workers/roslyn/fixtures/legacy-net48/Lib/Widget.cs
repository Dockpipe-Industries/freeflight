namespace Library {
#if LEGACY_PROJECT
public class Widget { public int Value => 42; public string XmlName => new System.Xml.Linq.XElement("legacy").Name.LocalName; }
#endif
}
