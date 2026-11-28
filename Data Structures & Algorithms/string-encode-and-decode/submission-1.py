class Solution:

    def encode(self, strs: List[str]) -> str:
        string = ""
        for x in strs:
            string += f"{len(x)}#{x}"
        return string
    def decode(self, s: str) -> List[str]:
        string = []
        i = 0
        while i < len(s):
            delim = s.find('#', i)
            length = int(s[i:delim])
            string.append(s[delim+1:delim+1+length])
            i = delim + 1 + length
        return string
